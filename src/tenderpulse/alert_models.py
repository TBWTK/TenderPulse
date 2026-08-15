from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tenderpulse.domain.matching import BlockerCode, GapCode, MatchDecision, MatchReason
from tenderpulse.domain.models import SourceCode


class AlertView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    profile_slug: str
    profile_version: int
    record_source: SourceCode
    record_source_id: str
    record_version: int
    title: str
    score: Decimal
    decision: MatchDecision
    reasons: tuple[MatchReason, ...]
    gaps: tuple[GapCode, ...]
    blockers: tuple[BlockerCode, ...]
    region_codes: tuple[str, ...]
    deadline_at: datetime | None
    source_url: str
    raw_sha256: str
    channel: str
    policy_version: str
    status: str
    created_at: datetime
    delivered_at: datetime | None
    read_at: datetime | None
