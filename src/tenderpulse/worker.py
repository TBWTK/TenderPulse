from __future__ import annotations

import logging
import signal
import threading
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import select

from tenderpulse.alerts import AlertService
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.live_ingestion import LiveIngestionService
from tenderpulse.runtime import create_database, create_raw_store, utc_now
from tenderpulse.settings import Settings
from tenderpulse.sources.http import OfficialSourceClient

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
        "worker_started live_ingestion_enabled=%s interval_seconds=%s",
        settings.live_ingestion_enabled,
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
            OfficialSourceClient(),
            now=utc_now,
        )

    def run_cycle() -> None:
        with factory() as session:
            session.execute(select(1))
        if service is None:
            raise RuntimeError("live ingestion service missing while scheduler is enabled")
        results = service.run_cycle(
            limit=settings.source_record_limit,
            ted_lookback_days=settings.ted_lookback_days,
            usa_lookback_days=settings.usa_lookback_days,
        )
        with factory.begin() as session:
            new_alerts = AlertService(session, now=utc_now).sync_all()
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

    run_scheduled_loop(
        enabled=settings.live_ingestion_enabled,
        interval_seconds=settings.ingestion_interval_seconds,
        stopped=stopped,
        run_cycle=run_cycle,
    )
    logger.info("worker_stopped")


if __name__ == "__main__":
    main()
