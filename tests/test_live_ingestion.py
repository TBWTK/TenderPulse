from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.live_ingestion import LiveIngestionService
from tenderpulse.persistence.models import Base, IngestionRunRow
from tenderpulse.persistence.repository import ProcurementRepository
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
        request_parameters = session.scalars(
            select(IngestionRunRow.request_parameters).order_by(IngestionRunRow.source)
        ).all()
    assert all(parameters["limit"] == 10 for parameters in request_parameters)


def test_known_fetch_failure_is_persisted_and_other_source_continues() -> None:
    factory = _factory()

    def now() -> datetime:
        return datetime(2026, 8, 8, 2, tzinfo=UTC)

    service = LiveIngestionService(
        IngestionCoordinator(factory, MemoryRawStore(), now=now),
        FailingTedClient(),
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
