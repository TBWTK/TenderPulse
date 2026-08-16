from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tenderpulse.domain.matching import current_opportunities
from tenderpulse.domain.models import SourceCode
from tenderpulse.human_reviews import (
    HumanReviewCandidate,
    HumanReviewConflict,
    HumanReviewLabel,
    HumanReviewNotFound,
    HumanReviewReason,
    HumanReviewSubmission,
    HumanReviewView,
)
from tenderpulse.persistence.models import (
    AccountRow,
    CompanyProfileRow,
    HumanReviewRow,
    ProcurementRecordRow,
    ProcurementVersionRow,
)
from tenderpulse.persistence.repository import ProcurementRepository


class HumanReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        *,
        account_id: UUID,
        profile_slug: str,
        source: SourceCode,
        source_record_id: str,
        submission: HumanReviewSubmission,
        at: datetime,
    ) -> HumanReviewView:
        _require_aware(at)
        account = self._session.scalar(
            select(AccountRow).where(
                AccountRow.id == account_id,
                AccountRow.active.is_(True),
                AccountRow.profile_slug == profile_slug,
            )
        )
        if account is None:
            raise HumanReviewNotFound("account profile is unavailable")

        profile = self._session.scalar(
            select(CompanyProfileRow).where(
                CompanyProfileRow.slug == profile_slug,
                CompanyProfileRow.version == submission.profile_version,
                CompanyProfileRow.active.is_(True),
            )
        )
        if profile is None:
            raise HumanReviewConflict("profile version is no longer current")

        record_pair = self._session.execute(
            select(ProcurementRecordRow, ProcurementVersionRow)
            .join(
                ProcurementVersionRow,
                ProcurementVersionRow.record_id == ProcurementRecordRow.id,
            )
            .where(
                ProcurementRecordRow.source == source.value,
                ProcurementRecordRow.source_record_id == source_record_id,
                ProcurementVersionRow.valid_to.is_(None),
            )
        ).one_or_none()
        if record_pair is None:
            raise HumanReviewNotFound("current procurement record not found")
        record, version = record_pair
        if (
            version.version != submission.record_version
            or version.raw_sha256 != submission.raw_sha256
        ):
            raise HumanReviewConflict("record version or raw evidence is no longer current")

        latest = self._latest_row(account_id, profile.id, version.id)
        current_revision = latest.revision if latest is not None else None
        if submission.expected_latest_revision != current_revision:
            raise HumanReviewConflict("human review revision changed; reload before saving")

        row = HumanReviewRow(
            account_id=account.id,
            profile_id=profile.id,
            record_version_id=version.id,
            supersedes_id=latest.id if latest is not None else None,
            revision=(latest.revision + 1) if latest is not None else 1,
            label=submission.label.value,
            reason=submission.reason.value,
            note=submission.note,
            created_at=at,
        )
        self._session.add(row)
        self._session.flush()
        return _to_view(row, profile, record, version)

    def list_for_account(self, account_id: UUID) -> tuple[HumanReviewView, ...]:
        statement = (
            select(
                HumanReviewRow,
                CompanyProfileRow,
                ProcurementRecordRow,
                ProcurementVersionRow,
            )
            .join(CompanyProfileRow, HumanReviewRow.profile_id == CompanyProfileRow.id)
            .join(
                ProcurementVersionRow,
                HumanReviewRow.record_version_id == ProcurementVersionRow.id,
            )
            .join(
                ProcurementRecordRow,
                ProcurementVersionRow.record_id == ProcurementRecordRow.id,
            )
            .where(HumanReviewRow.account_id == account_id)
            .order_by(HumanReviewRow.created_at, HumanReviewRow.revision)
        )
        return tuple(_to_view(*row) for row in self._session.execute(statement))

    def list_current_candidates(
        self,
        *,
        account_id: UUID,
        profile_slug: str,
    ) -> tuple[HumanReviewCandidate, ...]:
        profile = self._session.scalar(
            select(CompanyProfileRow).where(
                CompanyProfileRow.slug == profile_slug,
                CompanyProfileRow.active.is_(True),
            )
        )
        if profile is None:
            raise HumanReviewNotFound("account profile is unavailable")
        records = current_opportunities(ProcurementRepository(self._session).list_current_records())
        candidates: list[HumanReviewCandidate] = []
        for record in records:
            record_pair = self._session.execute(
                select(ProcurementRecordRow, ProcurementVersionRow)
                .join(
                    ProcurementVersionRow,
                    ProcurementVersionRow.record_id == ProcurementRecordRow.id,
                )
                .where(
                    ProcurementRecordRow.source == record.source.value,
                    ProcurementRecordRow.source_record_id == record.source_record_id,
                    ProcurementVersionRow.valid_to.is_(None),
                )
            ).one()
            record_row, version = record_pair
            latest = self._latest_row(account_id, profile.id, version.id)
            candidates.append(
                HumanReviewCandidate(
                    record=record,
                    profile_version=profile.version,
                    record_version=version.version,
                    raw_sha256=version.raw_sha256,
                    latest_review=(
                        _to_view(latest, profile, record_row, version)
                        if latest is not None
                        else None
                    ),
                )
            )
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    item.latest_review is not None,
                    item.record.source_record_id,
                ),
            )
        )

    def _latest_row(
        self,
        account_id: UUID,
        profile_id: UUID,
        record_version_id: UUID,
    ) -> HumanReviewRow | None:
        return self._session.scalar(
            select(HumanReviewRow)
            .where(
                HumanReviewRow.account_id == account_id,
                HumanReviewRow.profile_id == profile_id,
                HumanReviewRow.record_version_id == record_version_id,
            )
            .order_by(HumanReviewRow.revision.desc())
            .limit(1)
        )


def _to_view(
    row: HumanReviewRow,
    profile: CompanyProfileRow,
    record: ProcurementRecordRow,
    version: ProcurementVersionRow,
) -> HumanReviewView:
    return HumanReviewView(
        id=row.id,
        account_id=row.account_id,
        profile_slug=profile.slug,
        profile_version=profile.version,
        source=SourceCode(record.source),
        source_record_id=record.source_record_id,
        record_version=version.version,
        raw_sha256=version.raw_sha256,
        revision=row.revision,
        supersedes_id=row.supersedes_id,
        label=HumanReviewLabel(row.label),
        reason=HumanReviewReason(row.reason),
        note=row.note,
        created_at=_aware(row.created_at),
    )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("human review timestamp must include timezone")


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
