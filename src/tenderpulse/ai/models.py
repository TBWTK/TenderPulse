from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tenderpulse.ai.evidence import ExtractionClaims


class ExtractionStatus(StrEnum):
    VALIDATED = "validated"
    REJECTED = "rejected"
    FAILED = "failed"


class ExtractionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    record_key: str
    record_version_id: UUID
    record_version: int
    raw_sha256: str
    provider: str
    requested_model: str
    response_model: str | None
    prompt_version: str
    input_sha256: str
    output_sha256: str | None
    status: ExtractionStatus
    claims: ExtractionClaims | None
    error_code: str | None
    error_message: str | None
    retryable: bool
    created_at: datetime
