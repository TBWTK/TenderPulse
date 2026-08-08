from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.bootstrap import seed_demo
from tenderpulse.persistence.models import Base, IngestionRunRow, RawArtifactRow
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.raw_store import MemoryRawStore


def test_demo_seed_is_a_repeatable_end_to_end_vertical_slice() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    raw_store = MemoryRawStore()

    def now() -> datetime:
        return datetime(2026, 8, 8, 12, 0, tzinfo=UTC)

    first = seed_demo(factory, raw_store, now=now)
    with factory.begin() as session:
        repository = ProcurementRepository(session)
        current = repository.get_profile("it-data-integrator")
        assert current is not None
        repository.add_profile_version(
            current.model_copy(update={"version": 2, "name": "User configured profile"})
        )
    replay = seed_demo(factory, raw_store, now=now)

    with factory() as session:
        repository = ProcurementRepository(session)
        records = repository.list_current_records()
        profiles = repository.list_profiles()
        run_count = session.scalar(select(func.count()).select_from(IngestionRunRow))
        artifact_count = session.scalar(select(func.count()).select_from(RawArtifactRow))
        lineage_counts = [
            len(repository.lineage(record.source, record.source_record_id)) for record in records
        ]

    assert first.record_count == replay.record_count == 4
    assert len(records) == 4
    assert len(profiles) == 2
    assert next(profile for profile in profiles if profile.slug == "it-data-integrator").name == (
        "User configured profile"
    )
    assert (
        next(profile for profile in profiles if profile.slug == "it-data-integrator").version == 2
    )
    assert run_count == 6
    assert artifact_count == 3
    assert lineage_counts == [1, 1, 1, 1]
