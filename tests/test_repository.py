from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tenderpulse.domain.models import ProcurementRecord
from tenderpulse.persistence.models import Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_repository_persists_current_and_scd2_lineage(it_notice: ProcurementRecord) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    first_at = datetime(2026, 8, 8, tzinfo=UTC)
    second_at = first_at + timedelta(days=1)

    created = repository.apply_records((it_notice,), at=first_at)
    replay = repository.apply_records((it_notice,), at=second_at)
    updated = repository.apply_records(
        (it_notice.model_copy(update={"title": "Corrected cloud platform title"}),),
        at=second_at,
    )
    session.commit()

    current = repository.list_current_records()
    lineage = repository.lineage(it_notice.source, it_notice.source_record_id)

    assert [change.kind.value for change in created] == ["created"]
    assert [change.kind.value for change in replay] == ["unchanged"]
    assert [change.kind.value for change in updated] == ["updated"]
    assert len(current) == 1
    assert current[0].title == "Corrected cloud platform title"
    assert [version.version for version in lineage] == [1, 2]
    assert lineage[0].valid_to == second_at
    assert lineage[1].valid_to is None
    assert lineage[0].record.evidence.raw_sha256 == it_notice.evidence.raw_sha256
    all_lineages = repository.list_all_lineages()
    assert list(all_lineages) == [(it_notice.source, it_notice.source_record_id)]
    assert [
        version.version for version in all_lineages[(it_notice.source, it_notice.source_record_id)]
    ] == [
        1,
        2,
    ]


def test_repository_source_natural_key_isolated(it_notice: ProcurementRecord) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    at = datetime(2026, 8, 8, tzinfo=UTC)
    second = it_notice.model_copy(update={"source_record_id": "record-2"})

    repository.apply_records((it_notice, second), at=at)
    session.commit()

    assert [record.source_record_id for record in repository.list_current_records()] == [
        "record-1",
        "record-2",
    ]


def test_repository_creates_arbitrary_profile_and_preserves_version_history() -> None:
    session = _session()
    repository = ProcurementRepository(session)
    template = next(
        profile for profile in load_demo_profiles() if profile.slug == "cleaning-moscow"
    )
    created = template.model_copy(
        update={"slug": "user-facility-company", "name": "Пользовательский клининг"}
    )

    repository.create_profile(created)
    repository.add_profile_version(
        created.model_copy(update={"version": 2, "name": "Новый клининг"})
    )
    session.commit()

    assert repository.get_profile(created.slug).name == "Новый клининг"
    assert [item.version for item in repository.list_profile_history(created.slug)] == [1, 2]
    assert [item.name for item in repository.list_profile_history(created.slug)] == [
        "Пользовательский клининг",
        "Новый клининг",
    ]
