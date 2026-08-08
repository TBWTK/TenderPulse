from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceCode(StrEnum):
    TED = "ted"
    EIS = "eis"
    USA_SPENDING = "usaspending"


class RecordKind(StrEnum):
    NOTICE = "notice"
    AWARD = "award"


class LifecycleStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    AWARDED = "awarded"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


def _require_aware(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("datetime must include timezone evidence")
    return value


class ClassificationCode(BaseModel):
    model_config = ConfigDict(frozen=True)

    system: str = Field(min_length=1, max_length=32)
    code: str = Field(min_length=1, max_length=64)

    @field_validator("system")
    @classmethod
    def normalize_system(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = re.sub(r"[\s-]+", "", value).upper()
        if not normalized:
            raise ValueError("classification code cannot be empty")
        return normalized


class SourceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_sha256: str
    ingestion_run_id: UUID
    source_url: str = Field(min_length=1, max_length=2048)

    @field_validator("raw_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("raw_sha256 must be a lowercase hexadecimal SHA-256")
        return normalized

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        allowed = ("https://", "http://", "manual://")
        if not value.startswith(allowed):
            raise ValueError("source_url must use an allowed evidence scheme")
        return value


class Lot(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_lot_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1)
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    deadline_at: datetime | None = None
    classifications: tuple[ClassificationCode, ...] = ()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("deadline_at")
    @classmethod
    def validate_deadline(cls, value: datetime | None) -> datetime | None:
        return _require_aware(value)

    @model_validator(mode="after")
    def validate_money_pair(self) -> Self:
        if (self.amount is None) != (self.currency is None):
            raise ValueError("amount and currency must be known or unknown together")
        return self


class ProcurementRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceCode
    source_record_id: str = Field(min_length=1, max_length=512)
    kind: RecordKind
    lifecycle: LifecycleStatus
    title: str = Field(min_length=1)
    description: str = ""
    buyer_name: str | None = None
    supplier_names: tuple[str, ...] = ()
    classifications: tuple[ClassificationCode, ...] = ()
    countries: tuple[str, ...] = ()
    published_at: datetime | None = None
    observed_at: datetime
    deadline_at: datetime | None = None
    lots: tuple[Lot, ...] = Field(min_length=1)
    evidence: SourceEvidence

    @field_validator("published_at", "observed_at", "deadline_at")
    @classmethod
    def validate_timestamps(cls, value: datetime | None) -> datetime | None:
        return _require_aware(value)

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(code.strip().upper() for code in value if code.strip()))
        if any(len(code) != 2 for code in normalized):
            raise ValueError("countries must contain ISO 3166-1 alpha-2 codes")
        return normalized

    @property
    def natural_key(self) -> str:
        return f"{self.source.value}:{self.source_record_id}"

    def canonical_fingerprint(self) -> str:
        payload = self.model_dump(mode="json", exclude={"observed_at", "evidence"})
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(encoded).hexdigest()
