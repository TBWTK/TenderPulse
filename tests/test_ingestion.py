from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.domain.models import SourceCode
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.persistence.models import Base, IngestionRunRow, RawArtifactRow
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.raw_store import MemoryRawStore
from tenderpulse.sources.common import SourceContractError
from tenderpulse.sources.ted import parse_ted_response

FIXTURES = Path(__file__).parent / "fixtures"


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def test_ingestion_commits_raw_before_versioned_canonical() -> None:
    factory = _session_factory()
    raw_store = MemoryRawStore()
    coordinator = IngestionCoordinator(
        factory, raw_store, now=lambda: datetime(2026, 8, 8, tzinfo=UTC)
    )
    raw = (FIXTURES / "ted_search_medical.json").read_bytes()

    result = coordinator.ingest(
        source=SourceCode.TED,
        raw=raw,
        content_type="application/json",
        parser=parse_ted_response,
        request_parameters={"limit": 1, "fixture": True},
    )

    with factory() as session:
        run = session.get(IngestionRunRow, result.run_id)
        artifacts = session.scalars(select(RawArtifactRow)).all()
        records = ProcurementRepository(session).list_current_records()

    assert run is not None and run.status == "succeeded"
    assert run.record_count == 1
    assert len(artifacts) == 1
    assert raw_store.get(result.raw_sha256) == raw
    assert records[0].evidence.raw_sha256 == result.raw_sha256


def test_invalid_payload_preserves_failed_run_and_raw_evidence() -> None:
    factory = _session_factory()
    raw_store = MemoryRawStore()
    coordinator = IngestionCoordinator(
        factory, raw_store, now=lambda: datetime(2026, 8, 8, tzinfo=UTC)
    )

    with pytest.raises(SourceContractError):
        coordinator.ingest(
            source=SourceCode.TED,
            raw=b'{"notices":[{}]}',
            content_type="application/json",
            parser=parse_ted_response,
            request_parameters={"limit": 1},
        )

    with factory() as session:
        run = session.scalar(select(IngestionRunRow))
        artifact = session.scalar(select(RawArtifactRow))

    assert run is not None and run.status == "failed"
    assert run.error_code == "source_contract_error"
    assert artifact is not None
    assert raw_store.get(artifact.sha256) == b'{"notices":[{}]}'
