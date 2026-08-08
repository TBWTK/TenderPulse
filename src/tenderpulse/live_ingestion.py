from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import partial
from typing import Protocol
from uuid import UUID

from tenderpulse.domain.models import SourceCode
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.profiles import load_demo_profiles
from tenderpulse.sources.eis import parse_eis_package
from tenderpulse.sources.http import FetchResult, SourceFetchError
from tenderpulse.sources.ted import TED_SEARCH_URL, TedQuery, parse_ted_response
from tenderpulse.sources.usaspending import (
    USA_SPENDING_SEARCH_URL,
    USAspendingQuery,
    parse_usaspending_response,
)


class SourceClient(Protocol):
    def fetch_ted(self, query: TedQuery) -> FetchResult: ...

    def fetch_usaspending(self, query: USAspendingQuery) -> FetchResult: ...


@dataclass(frozen=True, slots=True)
class LiveSourceResult:
    source: SourceCode
    status: str
    run_id: UUID
    record_count: int
    error_code: str | None = None


class LiveIngestionService:
    def __init__(
        self,
        coordinator: IngestionCoordinator,
        source_client: SourceClient,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._coordinator = coordinator
        self._source_client = source_client
        self._now = now

    def run_cycle(
        self,
        *,
        limit: int,
        ted_lookback_days: int,
        usa_lookback_days: int,
        sources: tuple[SourceCode, ...] = (SourceCode.TED, SourceCode.USA_SPENDING),
    ) -> tuple[LiveSourceResult, ...]:
        today = self._now().date()
        profiles = load_demo_profiles()
        cpv_prefixes = tuple(
            dict.fromkeys(
                prefix
                for profile in profiles
                for prefix in profile.classification_prefixes.get("CPV", ())
            )
        )
        keywords = tuple(
            dict.fromkeys(keyword for profile in profiles for keyword in profile.positive_keywords)
        )
        ted_query = TedQuery(
            published_from=today - timedelta(days=ted_lookback_days),
            published_to=today,
            cpv_prefixes=cpv_prefixes,
            limit=limit,
        )
        usa_query = USAspendingQuery(
            action_from=today - timedelta(days=usa_lookback_days),
            action_to=today,
            keywords=keywords,
            limit=limit,
        )
        runners = {
            SourceCode.TED: lambda: self._run_ted(ted_query),
            SourceCode.USA_SPENDING: lambda: self._run_usaspending(usa_query),
        }
        unsupported = tuple(source for source in sources if source not in runners)
        if unsupported:
            names = ", ".join(source.value for source in unsupported)
            raise ValueError(f"live ingestion is not supported for: {names}")
        return tuple(runners[source]() for source in dict.fromkeys(sources))

    def ingest_eis_upload(self, *, raw: bytes, filename: str) -> LiveSourceResult:
        content_type = "application/zip" if raw.startswith(b"PK") else "application/xml"
        result = self._coordinator.ingest(
            source=SourceCode.EIS,
            raw=raw,
            content_type=content_type,
            parser=partial(parse_eis_package, source_filename=filename),
            request_parameters={
                "mode": "manual_upload",
                "filename": filename,
                "byte_size": len(raw),
            },
        )
        return LiveSourceResult(SourceCode.EIS, "succeeded", result.run_id, result.record_count)

    def _run_ted(self, query: TedQuery) -> LiveSourceResult:
        parameters = _parameters(query, endpoint=TED_SEARCH_URL)
        try:
            fetched = self._source_client.fetch_ted(query)
        except SourceFetchError as error:
            return self._record_fetch_failure(SourceCode.TED, parameters, error)
        result = self._coordinator.ingest(
            source=SourceCode.TED,
            raw=fetched.raw,
            content_type=fetched.content_type,
            parser=parse_ted_response,
            request_parameters=parameters,
        )
        return LiveSourceResult(SourceCode.TED, "succeeded", result.run_id, result.record_count)

    def _run_usaspending(self, query: USAspendingQuery) -> LiveSourceResult:
        parameters = _parameters(query, endpoint=USA_SPENDING_SEARCH_URL)
        try:
            fetched = self._source_client.fetch_usaspending(query)
        except SourceFetchError as error:
            return self._record_fetch_failure(SourceCode.USA_SPENDING, parameters, error)
        result = self._coordinator.ingest(
            source=SourceCode.USA_SPENDING,
            raw=fetched.raw,
            content_type=fetched.content_type,
            parser=parse_usaspending_response,
            request_parameters=parameters,
        )
        return LiveSourceResult(
            SourceCode.USA_SPENDING,
            "succeeded",
            result.run_id,
            result.record_count,
        )

    def _record_fetch_failure(
        self,
        source: SourceCode,
        parameters: dict[str, object],
        error: SourceFetchError,
    ) -> LiveSourceResult:
        run_id = self._coordinator.record_fetch_failure(
            source=source,
            request_parameters=parameters,
            error_code=error.code,
            error_message=str(error),
        )
        return LiveSourceResult(source, "failed", run_id, 0, error.code)


def _parameters(query: TedQuery | USAspendingQuery, *, endpoint: str) -> dict[str, object]:
    payload = query.model_dump(mode="json")
    payload["endpoint"] = endpoint
    payload["mode"] = "live_bounded"
    return payload


def bounded_lookback(today: date, days: int) -> tuple[date, date]:
    """Public helper used by UI/API filter validation without duplicating date arithmetic."""
    return today - timedelta(days=days), today
