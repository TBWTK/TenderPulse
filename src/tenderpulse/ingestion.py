from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.persistence.models import IngestionRunRow, RawArtifactRow
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.raw_store import RawStore
from tenderpulse.sources.common import SourceContractError, raw_sha256

Parser = Callable[..., tuple[ProcurementRecord, ...]]


@dataclass(frozen=True, slots=True)
class IngestionResult:
    run_id: UUID
    raw_sha256: str
    record_count: int


class IngestionCoordinator:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        raw_store: RawStore,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._session_factory = session_factory
        self._raw_store = raw_store
        self._now = now

    def ingest(
        self,
        *,
        source: SourceCode,
        raw: bytes,
        content_type: str,
        parser: Parser,
        request_parameters: dict[str, Any],
    ) -> IngestionResult:
        started_at = self._now()
        run_id = uuid4()
        with self._session_factory.begin() as session:
            session.add(
                IngestionRunRow(
                    id=run_id,
                    source=source.value,
                    status="running",
                    started_at=started_at,
                    observed_at=started_at,
                    request_parameters=request_parameters,
                    record_count=0,
                )
            )

        digest = raw_sha256(raw)
        try:
            object_uri = self._raw_store.put(
                source=source.value,
                sha256=digest,
                content=raw,
                content_type=content_type,
            )
            with self._session_factory.begin() as session:
                artifact = session.get(RawArtifactRow, digest)
                if artifact is None:
                    session.add(
                        RawArtifactRow(
                            sha256=digest,
                            source=source.value,
                            object_uri=object_uri,
                            byte_size=len(raw),
                            content_type=content_type,
                            created_at=self._now(),
                        )
                    )
                run = _required_run(session, run_id)
                run.raw_sha256 = digest

            records = parser(raw, ingestion_run_id=run_id, observed_at=started_at)
            finished_at = self._now()
            with self._session_factory.begin() as session:
                ProcurementRepository(session).apply_records(records, at=finished_at)
                run = _required_run(session, run_id)
                run.status = "succeeded"
                run.finished_at = finished_at
                run.record_count = len(records)
            return IngestionResult(run_id=run_id, raw_sha256=digest, record_count=len(records))
        except Exception as exc:
            self._mark_failed(run_id, exc)
            raise

    def record_fetch_failure(
        self,
        *,
        source: SourceCode,
        request_parameters: dict[str, Any],
        error_code: str,
        error_message: str,
    ) -> UUID:
        failed_at = self._now()
        run_id = uuid4()
        with self._session_factory.begin() as session:
            session.add(
                IngestionRunRow(
                    id=run_id,
                    source=source.value,
                    status="failed",
                    started_at=failed_at,
                    finished_at=failed_at,
                    observed_at=failed_at,
                    request_parameters=request_parameters,
                    record_count=0,
                    error_code=error_code,
                    error_message=error_message[:1000],
                )
            )
        return run_id

    def _mark_failed(self, run_id: UUID, exc: Exception) -> None:
        error_code = (
            "source_contract_error" if isinstance(exc, SourceContractError) else "unexpected_error"
        )
        with self._session_factory.begin() as session:
            run = _required_run(session, run_id)
            run.status = "failed"
            run.finished_at = self._now()
            run.error_code = error_code
            run.error_message = str(exc)[:1000]


def _required_run(session: Session, run_id: UUID) -> IngestionRunRow:
    run = session.get(IngestionRunRow, run_id)
    if run is None:
        raise RuntimeError(f"ingestion run {run_id} disappeared")
    return run
