from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.domain.models import SourceCode
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.live_ingestion import LiveIngestionService
from tenderpulse.persistence.models import Base, IngestionRunRow
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_mvp2_legacy_test_profiles as load_demo_profiles
from tenderpulse.raw_store import MemoryRawStore
from tenderpulse.sources.http import FetchResult, SourceFetchError


class FixtureSourceClient:
    def fetch_ted(self, query) -> FetchResult:
        return FetchResult(
            raw=files("tenderpulse.demo_data").joinpath("ted_active_notices.json").read_bytes(),
            content_type="application/json",
        )

    def fetch_usaspending(self, query) -> FetchResult:
        return FetchResult(
            raw=files("tenderpulse.demo_data").joinpath("usaspending_ai_award.json").read_bytes(),
            content_type="application/json",
        )

    def fetch_eis(self, query) -> FetchResult:
        return FetchResult(
            raw=(Path(__file__).parent / "fixtures" / "eis_search_rss.xml").read_bytes(),
            content_type="application/rss+xml",
        )


class FailingEisClient(FixtureSourceClient):
    def fetch_eis(self, query) -> FetchResult:
        raise SourceFetchError("eis_http_503", "EIS returned HTTP 503", retryable=True)


class CapturingSourceClient(FixtureSourceClient):
    def __init__(self) -> None:
        self.ted_queries = []
        self.usa_queries = []
        self.eis_queries = []

    def fetch_ted(self, query) -> FetchResult:
        self.ted_queries.append(query)
        return super().fetch_ted(query)

    def fetch_usaspending(self, query) -> FetchResult:
        self.usa_queries.append(query)
        return super().fetch_usaspending(query)

    def fetch_eis(self, query) -> FetchResult:
        self.eis_queries.append(query)
        return super().fetch_eis(query)


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def test_live_cycle_ingests_only_bounded_russian_eis_data() -> None:
    factory = _factory()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        FixtureSourceClient(),
        profiles=load_demo_profiles,
        now=now,
    )

    results = service.run_cycle(limit=10, eis_lookback_days=7)

    assert [(result.source.value, result.status, result.record_count) for result in results] == [
        ("eis", "succeeded", 2),
    ]
    with factory() as session:
        assert len(ProcurementRepository(session).list_current_records()) == 2
        runs = session.execute(
            select(IngestionRunRow.source, IngestionRunRow.request_parameters).order_by(
                IngestionRunRow.source
            )
        ).all()
    parameters_by_source = {source: parameters for source, parameters in runs}
    assert set(parameters_by_source) == {"eis"}
    assert parameters_by_source["eis"]["limit"] == 10
    assert parameters_by_source["eis"]["profile_versions"] == {
        profile.slug: 1 for profile in load_demo_profiles()
    }


def test_known_eis_fetch_failure_is_persisted() -> None:
    factory = _factory()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        FailingEisClient(),
        profiles=load_demo_profiles,
        now=now,
    )

    results = service.run_cycle(limit=5, eis_lookback_days=7)

    assert [(result.source.value, result.status) for result in results] == [
        ("eis", "failed"),
    ]
    with factory() as session:
        failed = session.scalar(select(IngestionRunRow).where(IngestionRunRow.source == "eis"))
    assert failed is not None
    assert failed.error_code == "eis_http_503"
    assert failed.raw_sha256 is None


def test_current_profile_versions_are_recorded_on_each_eis_cycle_without_restart() -> None:
    factory = _factory()
    current_profiles = list(load_demo_profiles())
    client = CapturingSourceClient()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        client,
        profiles=lambda: tuple(current_profiles),
        now=now,
    )
    service.run_cycle(limit=5, eis_lookback_days=7)

    current_profiles[:] = [
        current_profiles[0].model_copy(
            update={
                "version": 2,
                "classification_prefixes": {"CPV": ("99",)},
                "positive_keywords": ("quantum",),
            }
        ),
        *current_profiles[1:],
    ]
    service.run_cycle(limit=5, eis_lookback_days=7)

    assert len(client.eis_queries) == 2
    with factory() as session:
        runs = tuple(
            session.scalars(
                select(IngestionRunRow).order_by(IngestionRunRow.started_at, IngestionRunRow.id)
            )
        )
    recorded_versions = {
        run.request_parameters["profile_versions"]["auto-service-moscow"] for run in runs
    }
    assert recorded_versions == {1, 2}
    assert client.ted_queries == []
    assert client.usa_queries == []


@pytest.mark.parametrize(
    "profiles",
    [
        (),
        (load_demo_profiles()[0], load_demo_profiles()[0]),
    ],
)
def test_invalid_active_profile_set_fails_before_any_source_fetch(profiles) -> None:
    factory = _factory()
    client = CapturingSourceClient()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        client,
        profiles=lambda: profiles,
        now=now,
    )

    with pytest.raises(RuntimeError, match="distinct active company profiles"):
        service.run_cycle(limit=5, eis_lookback_days=7)

    assert client.ted_queries == []
    assert client.usa_queries == []
    assert client.eis_queries == []


def test_foreign_sources_are_rejected_before_live_fetch() -> None:
    factory = _factory()
    client = CapturingSourceClient()

    service = LiveIngestionService(
        IngestionCoordinator(
            factory,
            MemoryRawStore(),
            now=lambda: datetime(2026, 8, 8, 2, tzinfo=UTC),
        ),
        client,
        profiles=load_demo_profiles,
        now=lambda: datetime(2026, 8, 8, 2, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="MVP 2.0 live ingestion supports EIS only"):
        service.run_cycle(
            limit=5,
            eis_lookback_days=7,
            sources=(SourceCode.TED,),
        )

    assert client.ted_queries == []
    assert client.usa_queries == []
    assert client.eis_queries == []


def test_eis_limit_above_source_contract_fails_instead_of_silent_truncation() -> None:
    factory = _factory()
    client = CapturingSourceClient()
    service = LiveIngestionService(
        IngestionCoordinator(
            factory,
            MemoryRawStore(),
            now=lambda: datetime(2026, 8, 8, 2, tzinfo=UTC),
        ),
        client,
        profiles=load_demo_profiles,
        now=lambda: datetime(2026, 8, 8, 2, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="between 1 and 50"):
        service.run_cycle(limit=51)

    assert client.eis_queries == []
