from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from importlib.resources import files

from sqlalchemy.orm import Session, sessionmaker

from tenderpulse.alerts import AlertService
from tenderpulse.domain.models import SourceCode
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles
from tenderpulse.raw_store import RawStore
from tenderpulse.sources.eis import parse_eis_legacy_xml


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    run_count: int
    record_count: int


def seed_demo(
    session_factory: sessionmaker[Session],
    raw_store: RawStore,
    *,
    now: Callable[[], datetime],
) -> DemoSeedResult:
    coordinator = IngestionCoordinator(session_factory, raw_store, now=now)
    demo_root = files("tenderpulse.demo_data")
    inputs = (
        (
            SourceCode.EIS,
            demo_root.joinpath("eis_legacy_notification.xml").read_bytes(),
            "application/xml",
            partial(
                parse_eis_legacy_xml,
                source_url="manual://eis/demo/eis_legacy_notification.xml",
            ),
        ),
    )
    record_count = 0
    for source, raw, content_type, parser in inputs:
        result = coordinator.ingest(
            source=source,
            raw=raw,
            content_type=content_type,
            parser=parser,
            request_parameters={"mode": "demo_fixture", "limit": 7},
        )
        record_count += result.record_count

    with session_factory.begin() as session:
        ProcurementRepository(session).seed_profiles(load_demo_profiles())
        AlertService(session, now=now).sync_all()
    return DemoSeedResult(run_count=len(inputs), record_count=record_count)
