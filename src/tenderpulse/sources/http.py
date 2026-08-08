from __future__ import annotations

from dataclasses import dataclass

import httpx

from tenderpulse.sources.ted import TED_SEARCH_URL, TedQuery
from tenderpulse.sources.usaspending import USA_SPENDING_SEARCH_URL, USAspendingQuery


class SourceFetchError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class FetchResult:
    raw: bytes
    content_type: str


class OfficialSourceClient:
    def __init__(self, *, http_client: httpx.Client | None = None) -> None:
        self._http = http_client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
            headers={"User-Agent": "TenderPulse/0.1 (+bounded public-procurement research)"},
        )

    def fetch_ted(self, query: TedQuery) -> FetchResult:
        return self._post(TED_SEARCH_URL, query.to_payload(), source="ted")

    def fetch_usaspending(self, query: USAspendingQuery) -> FetchResult:
        return self._post(USA_SPENDING_SEARCH_URL, query.to_payload(), source="usaspending")

    def _post(self, url: str, payload: dict[str, object], *, source: str) -> FetchResult:
        try:
            response = self._http.post(
                url,
                headers={"Accept": "application/json"},
                json=payload,
            )
        except httpx.HTTPError as error:
            raise SourceFetchError(
                f"{source}_transport",
                f"{source} transport failed",
                retryable=True,
            ) from error
        if not response.is_success:
            status = response.status_code
            raise SourceFetchError(
                f"{source}_http_{status}",
                f"{source} returned HTTP {status}",
                retryable=status == 429 or status >= 500,
            )
        content_type = response.headers.get("content-type", "application/json").split(";", 1)[0]
        if content_type != "application/json":
            raise SourceFetchError(
                f"{source}_content_type",
                f"{source} returned unsupported content type",
                retryable=False,
            )
        return FetchResult(raw=response.content, content_type=content_type)
