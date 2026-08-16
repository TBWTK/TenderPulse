from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Protocol
from uuid import UUID

from tenderpulse.discovery import EisDiscoveryPlanItem, build_eis_discovery_plan
from tenderpulse.domain.models import SourceCode
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.profiles import CompanyProfile
from tenderpulse.sources.eis import parse_eis_package
from tenderpulse.sources.eis_rss import EIS_RSS_URL, EisRssQuery, parse_eis_rss
from tenderpulse.sources.http import FetchResult, SourceFetchError


class SourceClient(Protocol):
    def fetch_eis(self, query: EisRssQuery) -> FetchResult: ...


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
        profiles: Callable[[], tuple[CompanyProfile, ...]],
        now: Callable[[], datetime],
    ) -> None:
        self._coordinator = coordinator
        self._source_client = source_client
        self._profiles = profiles
        self._now = now

    def run_cycle(
        self,
        *,
        limit: int,
        eis_lookback_days: int = 7,
        sources: tuple[SourceCode, ...] = (SourceCode.EIS,),
    ) -> tuple[LiveSourceResult, ...]:
        if not 1 <= limit <= 50:
            raise ValueError("EIS live ingestion limit must be between 1 and 50")
        today = self._now().date()
        if not sources:
            raise ValueError("at least one live source is required")
        unsupported = tuple(source for source in sources if source is not SourceCode.EIS)
        if unsupported:
            raise ValueError("MVP 2.0 live ingestion supports EIS only")
        profiles = self._profiles()
        if not profiles or len({profile.slug for profile in profiles}) != len(profiles):
            raise RuntimeError("live ingestion requires distinct active company profiles")
        plan = build_eis_discovery_plan(profiles)
        results: list[LiveSourceResult] = []
        for _source in dict.fromkeys(sources):
            for item in plan:
                query = EisRssQuery(
                    published_from=today - timedelta(days=eis_lookback_days),
                    published_to=today,
                    limit=limit,
                    search_string=item.search_string,
                )
                results.append(self._run_eis(query, item))
        return tuple(results)

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

    def _run_eis(
        self,
        query: EisRssQuery,
        plan_item: EisDiscoveryPlanItem,
    ) -> LiveSourceResult:
        parameters = _parameters(
            query,
            endpoint=EIS_RSS_URL,
            plan_item=plan_item,
        )
        try:
            fetched = self._source_client.fetch_eis(query)
        except SourceFetchError as error:
            return self._record_fetch_failure(SourceCode.EIS, parameters, error)
        result = self._coordinator.ingest(
            source=SourceCode.EIS,
            raw=fetched.raw,
            content_type=fetched.content_type,
            parser=partial(parse_eis_rss, limit=query.limit),
            request_parameters=parameters,
        )
        return LiveSourceResult(SourceCode.EIS, "succeeded", result.run_id, result.record_count)

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


def _parameters(
    query: EisRssQuery,
    *,
    endpoint: str,
    plan_item: EisDiscoveryPlanItem | None = None,
) -> dict[str, object]:
    payload = query.model_dump(mode="json")
    payload["endpoint"] = endpoint
    payload["mode"] = "live_bounded"
    if plan_item is not None:
        payload["profile_slug"] = plan_item.profile_slug
        payload["profile_version"] = plan_item.profile_version
        payload["discovery_strategy_version"] = plan_item.strategy_version
    return payload
