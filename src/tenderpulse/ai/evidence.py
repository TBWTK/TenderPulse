from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from tenderpulse.domain.models import ProcurementRecord

PROMPT_VERSION = "tender-evidence-v2"


class EvidenceValidationError(ValueError):
    """The model output is structurally invalid or not supported by input evidence."""


class EvidenceInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_key: str
    raw_sha256: str
    fields: dict[str, str]
    input_sha256: str

    def render(self) -> str:
        return json.dumps(
            {
                "record_key": self.record_key,
                "raw_sha256": self.raw_sha256,
                "evidence_fields": self.fields,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = Field(min_length=1, max_length=256)
    quote: str = Field(min_length=1, max_length=1000)


class RequirementClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    mandatory: bool | None
    citation: Citation


class DeadlineClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=256)
    value: str = Field(min_length=1, max_length=512)
    normalized_at: datetime | None
    citation: Citation

    @field_validator("normalized_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("normalized deadline must include timezone evidence")
        return value


class EvidenceCoverageStatus(StrEnum):
    FOUND = "found"
    NOT_PRESENT = "not_present"
    UNKNOWN = "unknown"


class ExtractionClaims(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    requirements_status: EvidenceCoverageStatus
    requirements: tuple[RequirementClaim, ...]
    deadlines_status: EvidenceCoverageStatus
    deadlines: tuple[DeadlineClaim, ...]
    gaps: tuple[str, ...]

    @field_validator("gaps")
    @classmethod
    def validate_gaps(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("gaps cannot contain empty values")
        return normalized

    @model_validator(mode="after")
    def validate_coverage_statuses(self) -> Self:
        if (self.requirements_status is EvidenceCoverageStatus.FOUND) != bool(self.requirements):
            raise ValueError("requirements status must describe whether claims were found")
        if (self.deadlines_status is EvidenceCoverageStatus.FOUND) != bool(self.deadlines):
            raise ValueError("deadlines status must describe whether claims were found")
        return self


def build_evidence_input(record: ProcurementRecord) -> EvidenceInput:
    fields = {
        "title": record.title,
        "description": record.description or "unknown",
        "published_at": _render_datetime(record.published_at),
        "deadline_at": _render_datetime(record.deadline_at),
    }
    fields.update(
        {
            f"lot:{lot.source_lot_id}": json.dumps(
                lot.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for lot in record.lots
        }
    )
    hash_payload = json.dumps(
        {
            "record_key": record.natural_key,
            "raw_sha256": record.evidence.raw_sha256,
            "fields": fields,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return EvidenceInput(
        record_key=record.natural_key,
        raw_sha256=record.evidence.raw_sha256,
        fields=fields,
        input_sha256=hashlib.sha256(hash_payload).hexdigest(),
    )


def validate_extraction_arguments(
    evidence_input: EvidenceInput,
    arguments: dict[str, Any],
) -> ExtractionClaims:
    try:
        extraction = ExtractionClaims.model_validate(arguments)
    except ValidationError as error:
        raise EvidenceValidationError("structured extraction is invalid") from error

    citations = tuple(claim.citation for claim in extraction.requirements) + tuple(
        claim.citation for claim in extraction.deadlines
    )
    for citation in citations:
        field_value = evidence_input.fields.get(citation.field)
        if field_value is None:
            raise EvidenceValidationError(f"citation field is absent: {citation.field}")
        if citation.quote not in field_value:
            raise EvidenceValidationError(
                f"citation quote is not present in evidence field: {citation.field}"
            )
    return extraction


def upgrade_legacy_extraction_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Add explicit coverage to v1 payloads without inventing absence evidence."""
    upgraded = dict(payload)
    for category in ("requirements", "deadlines"):
        status_field = f"{category}_status"
        if status_field not in upgraded:
            upgraded[status_field] = "found" if upgraded.get(category) else "unknown"
    return upgraded


def _render_datetime(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.isoformat().replace("+00:00", "Z")
