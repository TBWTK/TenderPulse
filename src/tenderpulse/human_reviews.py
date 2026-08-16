from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tenderpulse.domain.matching import MatchDecision, Recommendation
from tenderpulse.domain.models import ProcurementRecord, SourceCode

MAX_HUMAN_REVIEW_SHORTLIST = 15
MAX_ACTIONABLE_REVIEWS = 10
CONTROL_REVIEW_TARGET = 5


class HumanReviewLabel(StrEnum):
    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class HumanReviewReason(StrEnum):
    SCOPE = "scope"
    GEOGRAPHY = "geography"
    BUDGET = "budget"
    QUALIFICATION = "qualification"
    DEADLINE = "deadline"
    MISSING_DATA = "missing_data"
    OTHER = "other"


class HumanReviewSubmission(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_version: int = Field(ge=1)
    record_version: int = Field(ge=1)
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_latest_revision: int | None = Field(default=None, ge=1)
    label: HumanReviewLabel
    reason: HumanReviewReason
    note: str = Field(min_length=3, max_length=1000)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        return " ".join(value.split())


class HumanReviewView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    account_id: UUID
    profile_slug: str
    profile_version: int
    source: SourceCode
    source_record_id: str
    record_version: int
    raw_sha256: str
    revision: int
    supersedes_id: UUID | None
    label: HumanReviewLabel
    reason: HumanReviewReason
    note: str
    created_at: datetime


class HumanReviewCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: ProcurementRecord
    profile_version: int
    record_version: int
    raw_sha256: str
    latest_review: HumanReviewView | None


class HumanReviewConflict(ValueError):
    pass


class HumanReviewNotFound(LookupError):
    pass


def build_human_review_shortlist(
    candidates: tuple[HumanReviewCandidate, ...],
    recommendations: tuple[Recommendation, ...],
) -> tuple[HumanReviewCandidate, ...]:
    candidate_by_key = {
        (item.record.source, item.record.source_record_id): item for item in candidates
    }
    recommendation_keys = [(item.record_source, item.record_source_id) for item in recommendations]
    if len(candidate_by_key) != len(candidates) or len(set(recommendation_keys)) != len(
        recommendation_keys
    ):
        raise RuntimeError("human review shortlist requires unique record identities")
    if set(candidate_by_key) != set(recommendation_keys):
        raise RuntimeError("human review candidates and recommendations must share one universe")

    actionable = [
        candidate_by_key[key]
        for key, recommendation in zip(recommendation_keys, recommendations, strict=True)
        if recommendation.decision in {MatchDecision.RECOMMENDED, MatchDecision.REVIEW}
    ]
    controls = [
        candidate_by_key[key]
        for key, recommendation in zip(recommendation_keys, recommendations, strict=True)
        if recommendation.decision not in {MatchDecision.RECOMMENDED, MatchDecision.REVIEW}
    ]
    selected = actionable[:MAX_ACTIONABLE_REVIEWS] + controls[:CONTROL_REVIEW_TARGET]
    selected_keys = {(item.record.source, item.record.source_record_id) for item in selected}
    if len(selected) < MAX_HUMAN_REVIEW_SHORTLIST:
        for candidate in (*actionable[MAX_ACTIONABLE_REVIEWS:], *controls[CONTROL_REVIEW_TARGET:]):
            key = (candidate.record.source, candidate.record.source_record_id)
            if key in selected_keys:
                continue
            selected.append(candidate)
            selected_keys.add(key)
            if len(selected) == MAX_HUMAN_REVIEW_SHORTLIST:
                break
    return tuple(selected)
