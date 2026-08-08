from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tenderpulse.ai.evidence import ExtractionClaims
from tenderpulse.ai.models import ExtractionOutcome, ExtractionStatus
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.persistence.models import (
    AIExtractionAttemptRow,
    ProcurementRecordRow,
    ProcurementVersionRow,
)


@dataclass(frozen=True)
class CurrentRecordContext:
    record: ProcurementRecord
    record_version_id: UUID
    record_version: int


class AIExtractionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_current_context(
        self,
        source: SourceCode,
        source_record_id: str,
    ) -> CurrentRecordContext | None:
        statement = (
            select(ProcurementVersionRow)
            .join(ProcurementRecordRow)
            .where(
                ProcurementRecordRow.source == source.value,
                ProcurementRecordRow.source_record_id == source_record_id,
                ProcurementVersionRow.valid_to.is_(None),
            )
        )
        row = self._session.scalar(statement)
        if row is None:
            return None
        return CurrentRecordContext(
            record=ProcurementRecord.model_validate(row.payload),
            record_version_id=row.id,
            record_version=row.version,
        )

    def find_validated(
        self,
        context: CurrentRecordContext,
        *,
        provider: str,
        requested_model: str,
        prompt_version: str,
        input_sha256: str,
    ) -> ExtractionOutcome | None:
        statement = select(AIExtractionAttemptRow).where(
            AIExtractionAttemptRow.record_version_id == context.record_version_id,
            AIExtractionAttemptRow.provider == provider,
            AIExtractionAttemptRow.requested_model == requested_model,
            AIExtractionAttemptRow.prompt_version == prompt_version,
            AIExtractionAttemptRow.input_sha256 == input_sha256,
            AIExtractionAttemptRow.status == ExtractionStatus.VALIDATED.value,
        )
        row = self._session.scalar(statement)
        return self._to_outcome(row, context) if row is not None else None

    def add_attempt(
        self,
        context: CurrentRecordContext,
        *,
        provider: str,
        requested_model: str,
        response_model: str | None,
        prompt_version: str,
        input_sha256: str,
        output_sha256: str | None,
        status: ExtractionStatus,
        claims: ExtractionClaims | None,
        error_code: str | None,
        error_message: str | None,
        retryable: bool,
        created_at: datetime,
    ) -> ExtractionOutcome:
        row = AIExtractionAttemptRow(
            record_version_id=context.record_version_id,
            provider=provider,
            requested_model=requested_model,
            response_model=response_model,
            prompt_version=prompt_version,
            input_sha256=input_sha256,
            output_sha256=output_sha256,
            raw_sha256=context.record.evidence.raw_sha256,
            status=status.value,
            payload=claims.model_dump(mode="json") if claims is not None else None,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
            created_at=created_at,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_outcome(row, context)

    def list_attempts(
        self,
        source: SourceCode,
        source_record_id: str,
    ) -> tuple[ExtractionOutcome, ...]:
        context = self.get_current_context(source, source_record_id)
        if context is None:
            return ()
        statement = (
            select(AIExtractionAttemptRow)
            .where(AIExtractionAttemptRow.record_version_id == context.record_version_id)
            .order_by(AIExtractionAttemptRow.created_at, AIExtractionAttemptRow.id)
        )
        return tuple(self._to_outcome(row, context) for row in self._session.scalars(statement))

    @staticmethod
    def _to_outcome(
        row: AIExtractionAttemptRow,
        context: CurrentRecordContext,
    ) -> ExtractionOutcome:
        payload: dict[str, Any] | None = row.payload
        return ExtractionOutcome(
            id=row.id,
            record_key=context.record.natural_key,
            record_version_id=context.record_version_id,
            record_version=context.record_version,
            raw_sha256=row.raw_sha256,
            provider=row.provider,
            requested_model=row.requested_model,
            response_model=row.response_model,
            prompt_version=row.prompt_version,
            input_sha256=row.input_sha256,
            output_sha256=row.output_sha256,
            status=ExtractionStatus(row.status),
            claims=ExtractionClaims.model_validate(payload) if payload is not None else None,
            error_code=row.error_code,
            error_message=row.error_message,
            retryable=row.retryable,
            created_at=_aware(row.created_at),
        )


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
