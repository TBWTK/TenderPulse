from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path

import httpx

from tenderpulse.sources.eis_rss import (
    EIS_RSS_URL,
    MAX_EIS_RSS_BYTES,
    EisRssQuery,
)
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
    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        eis_http_client: httpx.Client | None = None,
        eis_ca_files: tuple[Path, ...] = (),
    ) -> None:
        self._http = http_client or httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=False,
            headers={"User-Agent": "TenderPulse/0.1 (+bounded public-procurement research)"},
        )
        if eis_http_client is not None:
            self._eis_http = eis_http_client
        elif eis_ca_files:
            context = ssl.create_default_context()
            for ca_file in eis_ca_files:
                context.load_verify_locations(cafile=ca_file)
            self._eis_http = httpx.Client(
                verify=context,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=False,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; TenderPulse/0.1; bounded official RSS reader)"
                    )
                },
            )
        else:
            self._eis_http = self._http

    def fetch_ted(self, query: TedQuery) -> FetchResult:
        return self._post(TED_SEARCH_URL, query.to_payload(), source="ted")

    def fetch_usaspending(self, query: USAspendingQuery) -> FetchResult:
        return self._post(USA_SPENDING_SEARCH_URL, query.to_payload(), source="usaspending")

    def fetch_eis(self, query: EisRssQuery) -> FetchResult:
        try:
            with self._eis_http.stream(
                "GET",
                EIS_RSS_URL,
                params=query.to_params(),
                headers={"Accept": "application/rss+xml"},
            ) as response:
                if not response.is_success:
                    status = response.status_code
                    raise SourceFetchError(
                        f"eis_http_{status}",
                        f"eis returned HTTP {status}",
                        retryable=status == 429 or status >= 500,
                    )
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                if content_type not in {"application/rss+xml", "application/xml", "text/xml"}:
                    raise SourceFetchError(
                        "eis_content_type",
                        "eis returned unsupported content type",
                        retryable=False,
                    )
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        declared_bytes = int(content_length)
                    except ValueError as error:
                        raise SourceFetchError(
                            "eis_content_length",
                            "eis returned invalid content length",
                            retryable=False,
                        ) from error
                    if declared_bytes > MAX_EIS_RSS_BYTES:
                        raise SourceFetchError(
                            "eis_response_too_large",
                            "eis response exceeds the 2 MiB safety limit",
                            retryable=False,
                        )
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_EIS_RSS_BYTES:
                        raise SourceFetchError(
                            "eis_response_too_large",
                            "eis response exceeds the 2 MiB safety limit",
                            retryable=False,
                        )
        except httpx.HTTPError as error:
            raise SourceFetchError(
                "eis_transport",
                "eis transport failed",
                retryable=True,
            ) from error
        return FetchResult(raw=bytes(raw), content_type=content_type)

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
