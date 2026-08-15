from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tenderpulse.alerts import AlertService
from tenderpulse.persistence.alert_repository import AlertRepository
from tenderpulse.persistence.models import Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_mvp2_legacy_test_profiles as load_demo_profiles


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_in_app_alert_outbox_is_idempotent_and_traceable(it_notice) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    at = datetime(2026, 8, 8, tzinfo=UTC)
    repository.apply_records((it_notice,), at=at)
    repository.seed_profiles(load_demo_profiles())
    service = AlertService(session, now=lambda: at)

    first = service.sync_profile("it-russia-integrator")
    second = service.sync_profile("it-russia-integrator")
    session.commit()

    assert len(first) == 1
    assert second == ()
    alerts = AlertRepository(session).list_for_profile("it-russia-integrator")
    assert len(alerts) == 1
    assert alerts[0].record_source_id == it_notice.source_record_id
    assert alerts[0].raw_sha256 == it_notice.evidence.raw_sha256
    assert alerts[0].record_version == 1
    assert alerts[0].status == "delivered"
    assert alerts[0].region_codes == it_notice.region_codes
    assert alerts[0].deadline_at == it_notice.deadline_at
    assert alerts[0].source_url == it_notice.evidence.source_url
    assert alerts[0].blockers == ()


def test_new_record_version_can_create_a_new_alert(it_notice) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    at = datetime(2026, 8, 8, tzinfo=UTC)
    repository.apply_records((it_notice,), at=at)
    repository.seed_profiles(load_demo_profiles())
    AlertService(session, now=lambda: at).sync_profile("it-russia-integrator")
    repository.apply_records(
        (it_notice.model_copy(update={"title": "Updated cloud data platform"}),),
        at=at + timedelta(seconds=1),
    )

    created = AlertService(session, now=lambda: at + timedelta(seconds=2)).sync_profile(
        "it-russia-integrator"
    )
    session.commit()

    assert len(created) == 1
    assert [
        item.record_version
        for item in AlertRepository(session).list_for_profile("it-russia-integrator")
    ] == [2, 1]


def test_new_profile_version_creates_a_distinct_alert_snapshot(it_notice) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    at = datetime(2026, 8, 8, tzinfo=UTC)
    repository.apply_records((it_notice,), at=at)
    repository.seed_profiles(load_demo_profiles())
    first = AlertService(session, now=lambda: at).sync_profile("it-russia-integrator")
    current = repository.get_profile("it-russia-integrator")
    assert current is not None
    repository.add_profile_version(current.model_copy(update={"version": 2}))

    second = AlertService(session, now=lambda: at + timedelta(seconds=1)).sync_profile(
        "it-russia-integrator"
    )
    session.commit()

    assert [first[0].profile_version, second[0].profile_version] == [1, 2]
    assert len(AlertRepository(session).list_for_profile("it-russia-integrator")) == 2


def test_alert_can_be_marked_read(it_notice) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    at = datetime(2026, 8, 8, tzinfo=UTC)
    repository.apply_records((it_notice,), at=at)
    repository.seed_profiles(load_demo_profiles())
    alert = AlertService(session, now=lambda: at).sync_profile("it-russia-integrator")[0]

    read = AlertRepository(session).mark_read(alert.id, at=at + timedelta(minutes=1))
    session.commit()

    assert read is not None
    assert read.read_at == at + timedelta(minutes=1)
