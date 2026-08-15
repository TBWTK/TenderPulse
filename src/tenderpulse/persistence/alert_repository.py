from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from tenderpulse.alert_models import AlertView
from tenderpulse.domain.matching import Recommendation
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.persistence.models import (
    AlertEventRow,
    CompanyProfileRow,
    ProcurementRecordRow,
    ProcurementVersionRow,
)
from tenderpulse.profiles import CompanyProfile

POLICY_VERSION = "deterministic-match-v2-geography"
CHANNEL = "in_app"


class AlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_recommendation(
        self,
        profile: CompanyProfile,
        record: ProcurementRecord,
        recommendation: Recommendation,
        *,
        at: datetime,
    ) -> AlertView | None:
        profile_row = self._session.scalar(
            select(CompanyProfileRow).where(
                CompanyProfileRow.slug == profile.slug,
                CompanyProfileRow.version == profile.version,
            )
        )
        version_context = self._session.execute(
            select(ProcurementVersionRow, ProcurementRecordRow)
            .join(ProcurementRecordRow)
            .where(
                ProcurementRecordRow.source == record.source.value,
                ProcurementRecordRow.source_record_id == record.source_record_id,
                ProcurementVersionRow.valid_to.is_(None),
            )
        ).one_or_none()
        if profile_row is None or version_context is None:
            raise RuntimeError("alert references a profile or record version that is not persisted")
        version_row, record_row = version_context
        key = hashlib.sha256(
            f"{profile_row.id}:{version_row.id}:{CHANNEL}:{POLICY_VERSION}".encode()
        ).hexdigest()
        if (
            self._session.scalar(
                select(AlertEventRow.id).where(AlertEventRow.idempotency_key == key)
            )
            is not None
        ):
            return None
        row = AlertEventRow(
            idempotency_key=key,
            profile_id=profile_row.id,
            record_version_id=version_row.id,
            channel=CHANNEL,
            policy_version=POLICY_VERSION,
            status="delivered",
            payload={
                "title": record.title,
                "score": str(recommendation.score),
                "decision": recommendation.decision.value,
                "reasons": [reason.model_dump(mode="json") for reason in recommendation.reasons],
                "gaps": [gap.value for gap in recommendation.gaps],
                "blockers": [blocker.value for blocker in recommendation.blockers],
                "region_codes": list(record.region_codes),
                "deadline_at": (
                    record.deadline_at.isoformat() if record.deadline_at is not None else None
                ),
                "source_url": record.evidence.source_url,
                "raw_sha256": record.evidence.raw_sha256,
            },
            created_at=at,
            delivered_at=at,
            read_at=None,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_view(row, profile_row, version_row, record_row)

    def list_for_profile(self, profile_slug: str) -> tuple[AlertView, ...]:
        statement = (
            self._context_statement()
            .where(CompanyProfileRow.slug == profile_slug)
            .order_by(AlertEventRow.created_at.desc(), AlertEventRow.id)
        )
        return tuple(
            self._to_view(alert, profile, version, record)
            for alert, profile, version, record in self._session.execute(statement).all()
        )

    def list_all(self) -> tuple[AlertView, ...]:
        statement = self._context_statement().order_by(AlertEventRow.created_at, AlertEventRow.id)
        return tuple(
            self._to_view(alert, profile, version, record)
            for alert, profile, version, record in self._session.execute(statement).all()
        )

    def mark_read(
        self,
        alert_id: UUID,
        *,
        at: datetime,
        profile_slug: str | None = None,
    ) -> AlertView | None:
        row = self._context_for_id(alert_id, profile_slug=profile_slug)
        if row is None:
            return None
        alert, profile, version, record = row
        alert.read_at = at
        self._session.flush()
        return self._to_view(alert, profile, version, record)

    def _context_for_id(
        self,
        alert_id: UUID,
        *,
        profile_slug: str | None = None,
    ) -> (
        tuple[AlertEventRow, CompanyProfileRow, ProcurementVersionRow, ProcurementRecordRow] | None
    ):
        statement = self._context_statement().where(AlertEventRow.id == alert_id)
        if profile_slug is not None:
            statement = statement.where(CompanyProfileRow.slug == profile_slug)
        result = self._session.execute(statement).one_or_none()
        return result._tuple() if result is not None else None

    @staticmethod
    def _context_statement() -> Select[
        tuple[AlertEventRow, CompanyProfileRow, ProcurementVersionRow, ProcurementRecordRow]
    ]:
        return (
            select(
                AlertEventRow,
                CompanyProfileRow,
                ProcurementVersionRow,
                ProcurementRecordRow,
            )
            .join(CompanyProfileRow, AlertEventRow.profile_id == CompanyProfileRow.id)
            .join(
                ProcurementVersionRow,
                AlertEventRow.record_version_id == ProcurementVersionRow.id,
            )
            .join(ProcurementRecordRow, ProcurementVersionRow.record_id == ProcurementRecordRow.id)
        )

    @staticmethod
    def _to_view(
        row: AlertEventRow,
        profile: CompanyProfileRow,
        version: ProcurementVersionRow,
        record: ProcurementRecordRow,
    ) -> AlertView:
        payload = row.payload
        canonical_record = ProcurementRecord.model_validate(version.payload)
        return AlertView(
            id=row.id,
            profile_slug=profile.slug,
            profile_version=profile.version,
            record_source=SourceCode(record.source),
            record_source_id=record.source_record_id,
            record_version=version.version,
            title=payload["title"],
            score=payload["score"],
            decision=payload["decision"],
            reasons=payload["reasons"],
            gaps=payload["gaps"],
            blockers=payload.get("blockers", ()),
            region_codes=payload.get("region_codes", canonical_record.region_codes),
            deadline_at=payload.get("deadline_at", canonical_record.deadline_at),
            source_url=payload.get("source_url", canonical_record.evidence.source_url),
            raw_sha256=payload["raw_sha256"],
            channel=row.channel,
            policy_version=row.policy_version,
            status=row.status,
            created_at=_aware(row.created_at),
            delivered_at=_aware(row.delivered_at) if row.delivered_at is not None else None,
            read_at=_aware(row.read_at) if row.read_at is not None else None,
        )


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
