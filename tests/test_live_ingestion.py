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
from tenderpulse.profiles import load_demo_profiles
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


class FailingTedClient(FixtureSourceClient):
    def fetch_ted(self, query) -> FetchResult:
        raise SourceFetchError("ted_http_503", "TED returned HTTP 503", retryable=True)


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


def test_live_cycle_ingests_bounded_ted_eis_and_usaspending_data() -> None:
    factory = _factory()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        FixtureSourceClient(),
        profiles=load_demo_profiles,
        now=now,
    )

    results = service.run_cycle(limit=10, ted_lookback_days=14, usa_lookback_days=365)

    assert [(result.source.value, result.status, result.record_count) for result in results] == [
        ("ted", "succeeded", 2),
        ("eis", "succeeded", 2),
        ("usaspending", "succeeded", 1),
    ]
    with factory() as session:
        assert len(ProcurementRepository(session).list_current_records()) == 5
        runs = session.execute(
            select(IngestionRunRow.source, IngestionRunRow.request_parameters).order_by(
                IngestionRunRow.source
            )
        ).all()
    parameters_by_source = {source: parameters for source, parameters in runs}
    assert all(parameters["limit"] == 10 for parameters in parameters_by_source.values())
    assert parameters_by_source["ted"]["cpv_prefixes"] == ["48", "72", "33", "38"]
    assert parameters_by_source["ted"]["profile_versions"] == {
        "it-data-integrator": 1,
        "medlab-supplier": 1,
    }
    assert parameters_by_source["usaspending"]["keywords"] == [
        "data",
        "analytics",
        "cloud",
        "machine learning",
        "software",
        "кибербезопасность",
        "информационные технологии",
        "medical",
        "laboratory",
        "diagnostic",
        "reagent",
        "orthopaedic",
        "медицин",
        "лаборатор",
        "реагент",
    ]
    assert parameters_by_source["usaspending"]["profile_versions"] == {
        "it-data-integrator": 1,
        "medlab-supplier": 1,
    }


def test_known_fetch_failure_is_persisted_and_other_source_continues() -> None:
    factory = _factory()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        FailingTedClient(),
        profiles=load_demo_profiles,
        now=now,
    )

    results = service.run_cycle(limit=5, ted_lookback_days=7, usa_lookback_days=30)

    assert [(result.source.value, result.status) for result in results] == [
        ("ted", "failed"),
        ("eis", "succeeded"),
        ("usaspending", "succeeded"),
    ]
    with factory() as session:
        failed = session.scalar(select(IngestionRunRow).where(IngestionRunRow.source == "ted"))
    assert failed is not None
    assert failed.error_code == "ted_http_503"
    assert failed.raw_sha256 is None


def test_current_profile_versions_drive_each_new_live_query_without_restart() -> None:
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
    service.run_cycle(
        limit=5,
        ted_lookback_days=7,
        usa_lookback_days=30,
        sources=(SourceCode.TED, SourceCode.USA_SPENDING),
    )

    current_profiles[:] = [
        current_profiles[0].model_copy(
            update={
                "version": 2,
                "classification_prefixes": {"CPV": ("99",)},
                "positive_keywords": ("quantum",),
            }
        ),
        current_profiles[1].model_copy(
            update={
                "version": 2,
                "classification_prefixes": {"CPV": ("88",)},
                "positive_keywords": ("robotics", "quantum"),
            }
        ),
    ]
    service.run_cycle(
        limit=5,
        ted_lookback_days=7,
        usa_lookback_days=30,
        sources=(SourceCode.TED, SourceCode.USA_SPENDING),
    )

    assert client.ted_queries[0].cpv_prefixes == ("48", "72", "33", "38")
    assert client.ted_queries[1].cpv_prefixes == ("99", "88")
    assert client.usa_queries[1].keywords == ("quantum", "robotics")


@pytest.mark.parametrize(
    "profiles",
    [
        (),
        load_demo_profiles()[:1],
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

    with pytest.raises(RuntimeError, match="exactly two distinct active company profiles"):
        service.run_cycle(limit=5, ted_lookback_days=7, usa_lookback_days=30)

    assert client.ted_queries == []
    assert client.usa_queries == []
    assert client.eis_queries == []
