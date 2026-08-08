from __future__ import annotations

from tenderpulse.api import create_app
from tenderpulse.ingestion import IngestionCoordinator
from tenderpulse.live_ingestion import LiveIngestionService
from tenderpulse.runtime import (
    create_database,
    create_gigachat_client,
    create_raw_store,
    utc_now,
)
from tenderpulse.settings import Settings
from tenderpulse.sources.http import OfficialSourceClient

settings = Settings()
engine, session_factory = create_database(settings)
ingestion_runner = LiveIngestionService(
    IngestionCoordinator(session_factory, create_raw_store(settings), now=utc_now),
    OfficialSourceClient(),
    now=utc_now,
)
app = create_app(
    session_factory,
    now=utc_now,
    evidence_generator=create_gigachat_client(settings),
    ai_requested_model=settings.gigachat_model,
    ingestion_runner=ingestion_runner,
)
