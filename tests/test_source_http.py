from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from tenderpulse.sources.eis_rss import EIS_RSS_URL, MAX_EIS_RSS_BYTES, EisRssQuery
from tenderpulse.sources.http import OfficialSourceClient, SourceFetchError
from tenderpulse.sources.ted import TED_SEARCH_URL, TedQuery
from tenderpulse.sources.usaspending import USA_SPENDING_SEARCH_URL, USAspendingQuery


def test_official_source_client_posts_validated_ted_query_to_allowlisted_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"notices": []},
            headers={"content-type": "application/json"},
        )

    client = OfficialSourceClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    query = TedQuery(
        published_from=date(2026, 8, 1),
        published_to=date(2026, 8, 8),
        cpv_prefixes=("72",),
        limit=17,
    )

    result = client.fetch_ted(query)

    assert requests[0].url == httpx.URL(TED_SEARCH_URL)
    assert json.loads(requests[0].content) == query.to_payload()
    assert result.raw == b'{"notices":[]}'
    assert result.content_type == "application/json"


def test_official_source_client_posts_usaspending_outcome_query() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"results": []})

    client = OfficialSourceClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    query = USAspendingQuery(
        action_from=date(2026, 1, 1),
        action_to=date(2026, 8, 8),
        keywords=("machine learning",),
        limit=8,
    )

    result = client.fetch_usaspending(query)

    assert requests[0].url == httpx.URL(USA_SPENDING_SEARCH_URL)
    assert json.loads(requests[0].content) == query.to_payload()
    assert result.raw == b'{"results":[]}'


def test_official_source_client_gets_allowlisted_eis_rss_query() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            text='<rss version="2.0"><channel><item /></channel></rss>',
            headers={"content-type": "application/rss+xml;charset=UTF-8"},
        )

    transport = httpx.MockTransport(handler)
    client = OfficialSourceClient(
        http_client=httpx.Client(transport=transport),
        eis_http_client=httpx.Client(transport=transport),
    )
    query = EisRssQuery(
        published_from=date(2026, 8, 1),
        published_to=date(2026, 8, 8),
        limit=10,
        search_string="  уборка   помещений  ",
    )

    result = client.fetch_eis(query)

    assert requests[0].url.copy_with(query=None) == httpx.URL(EIS_RSS_URL)
    assert dict(requests[0].url.params) == query.to_params()
    assert query.to_params()["searchString"] == "уборка помещений"
    assert query.to_params()["morphology"] == "on"
    assert requests[0].headers["accept"] == "application/rss+xml"
    assert result.content_type == "application/rss+xml"


@pytest.mark.parametrize("search_string", ["", " ", "уборка\nпомещений", "я" * 201])
def test_eis_profile_search_rejects_unbounded_or_unsafe_text(search_string: str) -> None:
    with pytest.raises(ValueError):
        EisRssQuery(
            published_from=date(2026, 8, 1),
            published_to=date(2026, 8, 8),
            limit=10,
            search_string=search_string,
        )


@pytest.mark.parametrize(
    ("body", "content_type", "error_code"),
    [
        (b"<html>not rss</html>", "text/html", "eis_content_type"),
        (b"x" * (MAX_EIS_RSS_BYTES + 1), "application/rss+xml", "eis_response_too_large"),
    ],
)
def test_official_source_client_rejects_unsafe_eis_responses(
    body: bytes,
    content_type: str,
    error_code: str,
) -> None:
    client = OfficialSourceClient(
        eis_http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    content=body,
                    headers={"content-type": content_type},
                )
            )
        )
    )

    with pytest.raises(SourceFetchError) as captured:
        client.fetch_eis(
            EisRssQuery(
                published_from=date(2026, 8, 1),
                published_to=date(2026, 8, 8),
                limit=10,
            )
        )

    assert captured.value.code == error_code
    assert captured.value.retryable is False


def test_official_source_client_rejects_invalid_eis_content_length() -> None:
    client = OfficialSourceClient(
        eis_http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    content=b'<rss version="2.0"><channel /></rss>',
                    headers={
                        "content-type": "application/rss+xml",
                        "content-length": "not-a-number",
                    },
                )
            )
        )
    )

    with pytest.raises(SourceFetchError) as captured:
        client.fetch_eis(
            EisRssQuery(
                published_from=date(2026, 8, 1),
                published_to=date(2026, 8, 8),
                limit=10,
            )
        )

    assert captured.value.code == "eis_content_length"
    assert captured.value.retryable is False


@pytest.mark.parametrize("status,retryable", [(400, False), (429, True), (503, True)])
def test_official_source_client_returns_typed_safe_http_errors(
    status: int,
    retryable: bool,
) -> None:
    client = OfficialSourceClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status, text="upstream secret body")
            )
        )
    )

    with pytest.raises(SourceFetchError) as captured:
        client.fetch_ted(
            TedQuery(
                published_from=date(2026, 8, 1),
                published_to=date(2026, 8, 8),
                limit=1,
            )
        )

    assert captured.value.code == f"ted_http_{status}"
    assert captured.value.retryable is retryable
    assert "upstream secret body" not in str(captured.value)
