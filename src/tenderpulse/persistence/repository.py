from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from tenderpulse.domain.history import ChangeKind, ChangeResult, RecordVersion
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.persistence.models import (
    CompanyProfileRow,
    ProcurementRecordRow,
    ProcurementVersionRow,
)
from tenderpulse.profiles import CompanyProfile


class ProcurementRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def apply_records(
        self,
        records: tuple[ProcurementRecord, ...],
        *,
        at: datetime,
    ) -> tuple[ChangeResult, ...]:
        _require_aware(at)
        return tuple(self._apply_record(record, at=at) for record in records)

    def list_current_records(self) -> tuple[ProcurementRecord, ...]:
        statement = (
            select(ProcurementVersionRow)
            .join(ProcurementRecordRow)
            .where(ProcurementVersionRow.valid_to.is_(None))
            .order_by(ProcurementRecordRow.source, ProcurementRecordRow.source_record_id)
        )
        return tuple(
            ProcurementRecord.model_validate(row.payload)
            for row in self._session.scalars(statement)
        )

    def lineage(
        self,
        source: SourceCode,
        source_record_id: str,
    ) -> tuple[RecordVersion, ...]:
        statement = (
            select(ProcurementVersionRow)
            .join(ProcurementRecordRow)
            .where(
                ProcurementRecordRow.source == source.value,
                ProcurementRecordRow.source_record_id == source_record_id,
            )
            .order_by(ProcurementVersionRow.version)
        )
        return tuple(self._to_version(row) for row in self._session.scalars(statement))

    def replace_profiles(self, profiles: tuple[CompanyProfile, ...]) -> None:
        incoming = {(profile.slug, profile.version): profile for profile in profiles}
        existing = {
            (row.slug, row.version): row for row in self._session.scalars(select(CompanyProfileRow))
        }
        for key, existing_row in existing.items():
            existing_row.active = key in incoming
        for key, profile in incoming.items():
            profile_row = existing.get(key)
            payload = profile.model_dump(mode="json")
            if profile_row is None:
                self._session.add(
                    CompanyProfileRow(
                        slug=profile.slug,
                        version=profile.version,
                        payload=payload,
                        active=True,
                    )
                )
            else:
                profile_row.payload = payload
                profile_row.active = True

    def list_profiles(self) -> tuple[CompanyProfile, ...]:
        statement = (
            select(CompanyProfileRow)
            .where(CompanyProfileRow.active.is_(True))
            .order_by(CompanyProfileRow.slug)
        )
        return tuple(
            CompanyProfile.model_validate(row.payload) for row in self._session.scalars(statement)
        )

    def get_profile(self, slug: str) -> CompanyProfile | None:
        statement = (
            select(CompanyProfileRow)
            .where(CompanyProfileRow.slug == slug, CompanyProfileRow.active.is_(True))
            .order_by(CompanyProfileRow.version.desc())
            .limit(1)
        )
        row = self._session.scalar(statement)
        return CompanyProfile.model_validate(row.payload) if row is not None else None

    def add_profile_version(self, profile: CompanyProfile) -> None:
        current = self.get_profile(profile.slug)
        if current is None:
            raise LookupError(f"company profile not found: {profile.slug}")
        if profile.version != current.version + 1:
            raise ValueError("profile version must increment the active version by exactly one")
        for row in self._session.scalars(
            select(CompanyProfileRow).where(
                CompanyProfileRow.slug == profile.slug,
                CompanyProfileRow.active.is_(True),
            )
        ):
            row.active = False
        self._session.add(
            CompanyProfileRow(
                slug=profile.slug,
                version=profile.version,
                payload=profile.model_dump(mode="json"),
                active=True,
            )
        )
        self._session.flush()

    def _apply_record(self, record: ProcurementRecord, *, at: datetime) -> ChangeResult:
        statement = select(ProcurementRecordRow).where(
            ProcurementRecordRow.source == record.source.value,
            ProcurementRecordRow.source_record_id == record.source_record_id,
        )
        record_row = self._session.scalar(statement)
        fingerprint = record.canonical_fingerprint()
        if record_row is None:
            record_row = ProcurementRecordRow(
                source=record.source.value,
                source_record_id=record.source_record_id,
                kind=record.kind.value,
                current_version=1,
                created_at=at,
            )
            self._session.add(record_row)
            self._session.flush()
            version_row = self._new_version_row(record_row, record, 1, fingerprint, at)
            self._session.add(version_row)
            self._session.flush()
            return ChangeResult(ChangeKind.CREATED, self._to_version(version_row))

        current_statement = select(ProcurementVersionRow).where(
            ProcurementVersionRow.record_id == record_row.id,
            ProcurementVersionRow.valid_to.is_(None),
        )
        current = self._session.scalar(current_statement)
        if current is None:
            raise RuntimeError(f"record {record.natural_key} has no current version")
        if current.canonical_fingerprint == fingerprint:
            return ChangeResult(ChangeKind.UNCHANGED, self._to_version(current))
        current_from = _aware(current.valid_from)
        if at <= current_from:
            raise ValueError("new version time must be strictly after the current version")

        current.valid_to = at
        next_version = record_row.current_version + 1
        record_row.current_version = next_version
        record_row.kind = record.kind.value
        version_row = self._new_version_row(record_row, record, next_version, fingerprint, at)
        self._session.add(version_row)
        self._session.flush()
        return ChangeResult(ChangeKind.UPDATED, self._to_version(version_row))

    @staticmethod
    def _new_version_row(
        record_row: ProcurementRecordRow,
        record: ProcurementRecord,
        version: int,
        fingerprint: str,
        at: datetime,
    ) -> ProcurementVersionRow:
        return ProcurementVersionRow(
            record_id=record_row.id,
            version=version,
            canonical_fingerprint=fingerprint,
            payload=record.model_dump(mode="json"),
            raw_sha256=record.evidence.raw_sha256,
            ingestion_run_id=record.evidence.ingestion_run_id,
            valid_from=at,
            valid_to=None,
        )

    @staticmethod
    def _to_version(row: ProcurementVersionRow) -> RecordVersion:
        return RecordVersion(
            version=row.version,
            record=ProcurementRecord.model_validate(row.payload),
            canonical_fingerprint=row.canonical_fingerprint,
            valid_from=_aware(row.valid_from),
            valid_to=_aware(row.valid_to) if row.valid_to is not None else None,
        )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("persistence timestamp must include timezone")


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
