from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tenderpulse.domain.models import SourceCode


class IngestionRunView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    source: SourceCode
    status: str
    started_at: datetime
    finished_at: datetime | None
    observed_at: datetime
    request_parameters: dict[str, Any]
    record_count: int
    raw_sha256: str | None
    error_code: str | None
    error_message: str | None


class SourceFreshnessView(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceCode
    last_status: str
    last_started_at: datetime | None
    last_success_observed_at: datetime | None
    age_seconds: int | None
    last_record_count: int | None
    last_error_code: str | None
