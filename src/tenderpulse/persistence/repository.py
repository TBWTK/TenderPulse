from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from tenderpulse.domain.history import ChangeKind, ChangeResult, RecordVersion
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.domain.organizations import (
    display_organization_name,
    normalize_organization_name,
)
from tenderpulse.outcomes import AwardOutcomeView, build_award_outcome
from tenderpulse.persistence.models import (
    CompanyProfileRow,
    OrganizationAliasRow,
    OrganizationRow,
    ProcurementOrganizationLinkRow,
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

    def list_award_outcomes(self) -> tuple[AwardOutcomeView, ...]:
        records = (record for record in self.list_current_records() if record.kind.value == "award")
        return tuple(
            sorted(
                (build_award_outcome(record) for record in records),
                key=lambda outcome: outcome.observed_at,
                reverse=True,
            )
        )

    def backfill_organization_links(self, *, at: datetime) -> int:
        _require_aware(at)
        created = 0
        statement = select(ProcurementVersionRow).order_by(
            ProcurementVersionRow.valid_from,
            ProcurementVersionRow.record_id,
            ProcurementVersionRow.version,
        )
        for version_row in self._session.scalars(statement):
            record = ProcurementRecord.model_validate(version_row.payload)
            created += self._sync_organizations(record, version_row, at=at)
        return created

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

    def list_all_lineages(
        self,
    ) -> dict[tuple[SourceCode, str], tuple[RecordVersion, ...]]:
        statement = (
            select(ProcurementRecordRow, ProcurementVersionRow)
            .join(ProcurementVersionRow)
            .order_by(
                ProcurementRecordRow.source,
                ProcurementRecordRow.source_record_id,
                ProcurementVersionRow.version,
            )
        )
        grouped: dict[tuple[SourceCode, str], list[RecordVersion]] = {}
        for record_row, version_row in self._session.execute(statement):
            key = (SourceCode(record_row.source), record_row.source_record_id)
            grouped.setdefault(key, []).append(self._to_version(version_row))
        return {key: tuple(versions) for key, versions in grouped.items()}

    def seed_profiles(self, profiles: tuple[CompanyProfile, ...]) -> None:
        if len({profile.slug for profile in profiles}) != len(profiles):
            raise ValueError("seed profiles must have distinct slugs")
        existing_by_slug: dict[str, list[CompanyProfileRow]] = {}
        for row in self._session.scalars(select(CompanyProfileRow)):
            existing_by_slug.setdefault(row.slug, []).append(row)
        for profile in profiles:
            existing = existing_by_slug.get(profile.slug, [])
            if not existing:
                self._session.add(
                    CompanyProfileRow(
                        slug=profile.slug,
                        version=profile.version,
                        payload=profile.model_dump(mode="json"),
                        active=True,
                    )
                )
                continue
            active_count = sum(row.active for row in existing)
            if active_count != 1:
                raise RuntimeError(f"profile {profile.slug} must have exactly one active version")

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
            self._sync_organizations(record, version_row, at=at)
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
        self._sync_organizations(record, version_row, at=at)
        return ChangeResult(ChangeKind.UPDATED, self._to_version(version_row))

    def _sync_organizations(
        self,
        record: ProcurementRecord,
        version_row: ProcurementVersionRow,
        *,
        at: datetime,
    ) -> int:
        created_links = 0
        names: list[tuple[str, int, str]] = []
        if record.buyer_name and record.buyer_name.strip():
            names.append(("buyer", 0, record.buyer_name))
        seen_suppliers: set[str] = set()
        for supplier_name in record.supplier_names:
            display = display_organization_name(supplier_name)
            if display in seen_suppliers:
                continue
            seen_suppliers.add(display)
            names.append(("supplier", len(seen_suppliers) - 1, display))

        for role, ordinal, source_name in names:
            display = display_organization_name(source_name)
            normalized = normalize_organization_name(display)
            organization = self._session.scalar(
                select(OrganizationRow).where(
                    OrganizationRow.source == record.source.value,
                    OrganizationRow.normalized_name == normalized,
                )
            )
            if organization is None:
                organization = OrganizationRow(
                    source=record.source.value,
                    canonical_name=display,
                    normalized_name=normalized,
                    created_at=at,
                )
                self._session.add(organization)
                self._session.flush()

            alias = self._session.scalar(
                select(OrganizationAliasRow).where(
                    OrganizationAliasRow.organization_id == organization.id,
                    OrganizationAliasRow.alias_name == display,
                )
            )
            if alias is None:
                alias = OrganizationAliasRow(
                    organization_id=organization.id,
                    alias_name=display,
                    normalized_alias=normalized,
                    created_at=at,
                )
                self._session.add(alias)
                self._session.flush()

            existing_link = self._session.scalar(
                select(ProcurementOrganizationLinkRow).where(
                    ProcurementOrganizationLinkRow.record_version_id == version_row.id,
                    ProcurementOrganizationLinkRow.role == role,
                    ProcurementOrganizationLinkRow.ordinal == ordinal,
                )
            )
            if existing_link is None:
                self._session.add(
                    ProcurementOrganizationLinkRow(
                        record_version_id=version_row.id,
                        organization_id=organization.id,
                        alias_id=alias.id,
                        role=role,
                        ordinal=ordinal,
                        source_name=display,
                        raw_sha256=record.evidence.raw_sha256,
                    )
                )
                created_links += 1
            elif (
                existing_link.organization_id != organization.id
                or existing_link.alias_id != alias.id
                or existing_link.source_name != display
                or existing_link.raw_sha256 != record.evidence.raw_sha256
            ):
                raise RuntimeError("organization link conflicts with immutable record version")
        return created_links

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
