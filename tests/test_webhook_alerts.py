from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tenderpulse.alert_delivery import WebhookAlertDispatcher
from tenderpulse.alerts import AlertService
from tenderpulse.domain.models import ProcurementRecord
from tenderpulse.persistence.models import AlertDeliveryAttemptRow, Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_mvp2_legacy_test_profiles as load_demo_profiles
from tenderpulse.settings import Settings


def _session_with_alert(record: ProcurementRecord) -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    repository = ProcurementRepository(session)
    repository.apply_records((record,), at=datetime(2026, 8, 8, tzinfo=UTC))
    repository.seed_profiles(load_demo_profiles())
    AlertService(session, now=lambda: datetime(2026, 8, 8, tzinfo=UTC)).sync_profile(
        "it-russia-integrator"
    )
    session.commit()
    return session


def test_webhook_delivery_is_opt_in_idempotent_and_audited_without_destination(
    it_notice: ProcurementRecord,
) -> None:
    session = _session_with_alert(it_notice)
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204, text="sensitive response body")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        dispatcher = WebhookAlertDispatcher(
            session,
            client=client,
            webhook_url="https://alerts.example.test/tenderpulse",
            now=lambda: datetime(2026, 8, 8, 1, tzinfo=UTC),
            max_attempts=3,
        )
        delivered = dispatcher.dispatch_pending()
        replay = dispatcher.dispatch_pending()
        session.commit()

    attempt = session.scalar(select(AlertDeliveryAttemptRow))
    assert attempt is not None
    assert len(delivered) == 1
    assert replay == ()
    assert len(requests) == 1
    assert requests[0].headers["Idempotency-Key"] == delivered[0].idempotency_key
    assert json.loads(requests[0].content)["alert"]["raw_sha256"] == (it_notice.evidence.raw_sha256)
    assert attempt.status == "delivered"
    assert attempt.http_status == 204
    assert (
        attempt.destination_sha256
        == hashlib.sha256(b"https://alerts.example.test/tenderpulse").hexdigest()
    )
    assert "sensitive response body" not in repr(attempt.__dict__)
    assert "alerts.example.test" not in repr(attempt.__dict__)


def test_retryable_webhook_failure_keeps_attempt_history_and_stable_key(
    it_notice: ProcurementRecord,
) -> None:
    session = _session_with_alert(it_notice)
    statuses = iter((503, 202))

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(next(statuses))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        dispatcher = WebhookAlertDispatcher(
            session,
            client=client,
            webhook_url="https://alerts.example.test/tenderpulse",
            now=lambda: datetime(2026, 8, 8, 1, tzinfo=UTC),
            max_attempts=3,
        )
        failed = dispatcher.dispatch_pending()
        delivered = dispatcher.dispatch_pending()
        session.commit()

    attempts = tuple(
        session.scalars(
            select(AlertDeliveryAttemptRow).order_by(AlertDeliveryAttemptRow.attempt_number)
        )
    )
    assert failed[0].status == "failed"
    assert failed[0].retryable is True
    assert delivered[0].status == "delivered"
    assert [attempt.http_status for attempt in attempts] == [503, 202]
    assert attempts[0].idempotency_key == attempts[1].idempotency_key


def test_webhook_requires_https_and_settings_disable_it_by_default(
    it_notice: ProcurementRecord,
) -> None:
    settings = Settings(_env_file=None)
    assert settings.alert_webhook_url is None
    with httpx.Client() as client, pytest.raises(ValueError, match="HTTPS"):
        WebhookAlertDispatcher(
            _session_with_alert(it_notice),
            client=client,
            webhook_url="http://alerts.example.test/hook",
            now=lambda: datetime(2026, 8, 8, tzinfo=UTC),
        )
