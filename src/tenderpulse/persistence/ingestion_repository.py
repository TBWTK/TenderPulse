from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from tenderpulse.domain.models import SourceCode
from tenderpulse.ingestion_models import IngestionRunView, SourceFreshnessView
from tenderpulse.persistence.models import IngestionRunRow
from tenderpulse.source_policy import CURRENT_PRODUCT_SOURCES


class IngestionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_runs(self, *, limit: int = 50) -> tuple[IngestionRunView, ...]:
        statement = select(IngestionRunRow).order_by(IngestionRunRow.started_at.desc()).limit(limit)
        return tuple(self._to_view(row) for row in self._session.scalars(statement))

    def list_current_product_runs(self, *, limit: int = 50) -> tuple[IngestionRunView, ...]:
        current_sources = tuple(source.value for source in CURRENT_PRODUCT_SOURCES)
        statement = (
            select(IngestionRunRow)
            .where(IngestionRunRow.source.in_(current_sources))
            .order_by(IngestionRunRow.started_at.desc())
            .limit(limit)
        )
        return tuple(self._to_view(row) for row in self._session.scalars(statement))

    def source_freshness(self, *, now: datetime) -> tuple[SourceFreshnessView, ...]:
        rows = tuple(
            self._session.scalars(
                select(IngestionRunRow).order_by(IngestionRunRow.started_at.desc())
            )
        )
        result: list[SourceFreshnessView] = []
        for source in CURRENT_PRODUCT_SOURCES:
            source_rows = tuple(row for row in rows if row.source == source.value)
            latest = source_rows[0] if source_rows else None
            latest_success = next(
                (row for row in source_rows if row.status == "succeeded"),
                None,
            )
            success_observed = (
                _aware(latest_success.observed_at) if latest_success is not None else None
            )
            age_seconds = (
                max(0, int((now - success_observed).total_seconds()))
                if success_observed is not None
                else None
            )
            result.append(
                SourceFreshnessView(
                    source=source,
                    last_status=latest.status if latest is not None else "unknown",
                    last_started_at=_aware(latest.started_at) if latest is not None else None,
                    last_success_observed_at=success_observed,
                    age_seconds=age_seconds,
                    last_record_count=latest.record_count if latest is not None else None,
                    last_error_code=latest.error_code if latest is not None else None,
                )
            )
        return tuple(result)

    @staticmethod
    def _to_view(row: IngestionRunRow) -> IngestionRunView:
        return IngestionRunView(
            id=row.id,
            source=SourceCode(row.source),
            status=row.status,
            started_at=_aware(row.started_at),
            finished_at=_aware(row.finished_at) if row.finished_at is not None else None,
            observed_at=_aware(row.observed_at),
            request_parameters=row.request_parameters,
            record_count=row.record_count,
            raw_sha256=row.raw_sha256,
            error_code=row.error_code,
            error_message=row.error_message,
        )


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
