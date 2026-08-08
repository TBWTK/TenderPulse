from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from tenderpulse.domain.models import ProcurementRecord


class ChangeKind(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class RecordVersion:
    version: int
    record: ProcurementRecord
    canonical_fingerprint: str
    valid_from: datetime
    valid_to: datetime | None


@dataclass(frozen=True, slots=True)
class ChangeResult:
    kind: ChangeKind
    version: RecordVersion


class VersionHistory:
    """In-memory executable specification for SCD2 behavior.

    PostgreSQL persistence must preserve these semantics. This object is deliberately small enough
    to serve as the regression oracle for repository implementations.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[RecordVersion]] = {}

    def apply(self, record: ProcurementRecord, *, at: datetime) -> ChangeResult:
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("version timestamp must include timezone")

        fingerprint = record.canonical_fingerprint()
        versions = self._versions.setdefault(record.natural_key, [])
        if not versions:
            created = RecordVersion(
                version=1,
                record=record,
                canonical_fingerprint=fingerprint,
                valid_from=at,
                valid_to=None,
            )
            versions.append(created)
            return ChangeResult(ChangeKind.CREATED, created)

        current = versions[-1]
        if current.canonical_fingerprint == fingerprint:
            return ChangeResult(ChangeKind.UNCHANGED, current)
        if at <= current.valid_from:
            raise ValueError("new version time must be strictly after the current version")

        versions[-1] = replace(current, valid_to=at)
        updated = RecordVersion(
            version=current.version + 1,
            record=record,
            canonical_fingerprint=fingerprint,
            valid_from=at,
            valid_to=None,
        )
        versions.append(updated)
        return ChangeResult(ChangeKind.UPDATED, updated)

    def versions_for(self, natural_key: str) -> tuple[RecordVersion, ...]:
        return tuple(self._versions.get(natural_key, ()))
