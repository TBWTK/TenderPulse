from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

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
