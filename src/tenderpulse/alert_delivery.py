from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tenderpulse.alert_models import AlertView
from tenderpulse.persistence.alert_repository import AlertRepository
from tenderpulse.persistence.models import AlertDeliveryAttemptRow


class WebhookDeliveryView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    alert_event_id: UUID
    attempt_number: int
    idempotency_key: str
    status: str
    http_status: int | None
    error_code: str | None
    retryable: bool
    created_at: datetime
    finished_at: datetime


class WebhookAlertDispatcher:
    def __init__(
        self,
        session: Session,
        *,
        client: httpx.Client,
        webhook_url: str,
        now: Callable[[], datetime],
        max_attempts: int = 5,
        timeout_seconds: float = 10.0,
    ) -> None:
        parsed = urlsplit(webhook_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError(
                "alert webhook URL must be an HTTPS URL without credentials or fragment"
            )
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self._session = session
        self._client = client
        self._webhook_url = webhook_url
        self._destination_sha256 = hashlib.sha256(webhook_url.encode()).hexdigest()
        self._now = now
        self._max_attempts = max_attempts
        self._timeout_seconds = timeout_seconds

    def dispatch_pending(self) -> tuple[WebhookDeliveryView, ...]:
        delivered: list[WebhookDeliveryView] = []
        for alert in AlertRepository(self._session).list_all():
            latest = self._session.scalar(
                select(AlertDeliveryAttemptRow)
                .where(
                    AlertDeliveryAttemptRow.alert_event_id == alert.id,
                    AlertDeliveryAttemptRow.destination_sha256 == self._destination_sha256,
                )
                .order_by(AlertDeliveryAttemptRow.attempt_number.desc())
                .limit(1)
            )
            if latest is not None and (latest.status == "delivered" or not latest.retryable):
                continue
            attempted = self._session.scalar(
                select(func.count())
                .select_from(AlertDeliveryAttemptRow)
                .where(
                    AlertDeliveryAttemptRow.alert_event_id == alert.id,
                    AlertDeliveryAttemptRow.destination_sha256 == self._destination_sha256,
                )
            )
            attempt_number = int(attempted or 0) + 1
            if attempt_number > self._max_attempts:
                continue
            delivered.append(self._deliver(alert, attempt_number=attempt_number))
        return tuple(delivered)

    def _deliver(self, alert: AlertView, *, attempt_number: int) -> WebhookDeliveryView:
        at = self._now()
        idempotency_key = hashlib.sha256(
            f"{alert.id}:webhook:{self._destination_sha256}".encode()
        ).hexdigest()
        attempt = AlertDeliveryAttemptRow(
            alert_event_id=alert.id,
            channel="webhook",
            destination_sha256=self._destination_sha256,
            attempt_number=attempt_number,
            idempotency_key=idempotency_key,
            status="started",
            http_status=None,
            error_code=None,
            retryable=True,
            created_at=at,
            finished_at=None,
        )
        self._session.add(attempt)
        self._session.flush()
        try:
            response = self._client.post(
                self._webhook_url,
                json={
                    "event": "tenderpulse.recommendation",
                    "idempotency_key": idempotency_key,
                    "alert": alert.model_dump(mode="json"),
                },
                headers={"Idempotency-Key": idempotency_key},
                timeout=self._timeout_seconds,
            )
            attempt.http_status = response.status_code
            if 200 <= response.status_code < 300:
                attempt.status = "delivered"
                attempt.retryable = False
            else:
                attempt.status = "failed"
                attempt.error_code = "http_status"
                attempt.retryable = response.status_code == 429 or response.status_code >= 500
        except httpx.HTTPError:
            attempt.status = "failed"
            attempt.error_code = "transport_error"
            attempt.retryable = True
        attempt.finished_at = self._now()
        self._session.flush()
        return self._to_view(attempt)

    @staticmethod
    def _to_view(row: AlertDeliveryAttemptRow) -> WebhookDeliveryView:
        if row.finished_at is None:
            raise RuntimeError("webhook attempt did not reach a terminal state")
        return WebhookDeliveryView(
            id=row.id,
            alert_event_id=row.alert_event_id,
            attempt_number=row.attempt_number,
            idempotency_key=row.idempotency_key,
            status=row.status,
            http_status=row.http_status,
            error_code=row.error_code,
            retryable=row.retryable,
            created_at=_aware(row.created_at),
            finished_at=_aware(row.finished_at),
        )


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
