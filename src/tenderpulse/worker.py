from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Callable
from typing import Protocol

import httpx
from sqlalchemy import select

from tenderpulse.alert_delivery import WebhookAlertDispatcher, WebhookDeliveryView
from tenderpulse.alerts import AlertService
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.live_ingestion import LiveIngestionService
from tenderpulse.runtime import (
    create_database,
    create_official_source_client,
    create_profile_provider,
    create_raw_store,
    utc_now,
)
from tenderpulse.settings import Settings

logger = logging.getLogger("tenderpulse.worker")


class StopSignal(Protocol):
    def is_set(self) -> bool: ...

    def wait(self, seconds: int) -> bool: ...


def run_scheduled_loop(
    *,
    enabled: bool,
    interval_seconds: int,
    stopped: StopSignal,
    run_cycle: Callable[[], object],
) -> None:
    while not stopped.is_set():
        if enabled:
            run_cycle()
        stopped.wait(interval_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    _, factory = create_database(settings)
    stopped = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stopped.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    logger.info(
        "worker_started live_ingestion_enabled=%s webhook_enabled=%s interval_seconds=%s",
        settings.live_ingestion_enabled,
        settings.alert_webhook_url is not None,
        settings.ingestion_interval_seconds,
    )

    service: LiveIngestionService | None = None
    if settings.live_ingestion_enabled:
        service = LiveIngestionService(
            IngestionCoordinator(
                factory,
                create_raw_store(settings),
                now=utc_now,
            ),
            create_official_source_client(settings),
            profiles=create_profile_provider(factory),
            now=utc_now,
        )

    def run_cycle() -> None:
        with factory() as session:
            session.execute(select(1))
        results = (
            service.run_cycle(
                limit=settings.source_record_limit,
                eis_lookback_days=settings.eis_lookback_days,
            )
            if service is not None
            else ()
        )
        with factory.begin() as session:
            new_alerts = AlertService(session, now=utc_now).sync_all()
            webhook_deliveries: tuple[WebhookDeliveryView, ...] = ()
            if settings.alert_webhook_url is not None:
                with httpx.Client() as client:
                    webhook_deliveries = WebhookAlertDispatcher(
                        session,
                        client=client,
                        webhook_url=settings.alert_webhook_url.get_secret_value(),
                        now=utc_now,
                        max_attempts=settings.alert_webhook_max_attempts,
                        timeout_seconds=settings.alert_webhook_timeout_seconds,
                    ).dispatch_pending()
        for result in results:
            logger.info(
                "ingestion_cycle source=%s status=%s run_id=%s record_count=%s error_code=%s",
                result.source.value,
                result.status,
                result.run_id,
                result.record_count,
                result.error_code,
            )
        logger.info("alert_sync new_deliveries=%s", len(new_alerts))
        if settings.alert_webhook_url is not None:
            logger.info(
                "webhook_alert_dispatch attempts=%s delivered=%s failed=%s",
                len(webhook_deliveries),
                sum(delivery.status == "delivered" for delivery in webhook_deliveries),
                sum(delivery.status == "failed" for delivery in webhook_deliveries),
            )

    run_scheduled_loop(
        enabled=settings.live_ingestion_enabled or settings.alert_webhook_url is not None,
        interval_seconds=settings.ingestion_interval_seconds,
        stopped=stopped,
        run_cycle=run_cycle,
    )
    logger.info("worker_stopped")


if __name__ == "__main__":
    main()
