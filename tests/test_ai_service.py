from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tenderpulse.ai.gigachat import GeneratedArguments, GigaChatError
from tenderpulse.ai.service import AIExtractionService, ExtractionStatus
from tenderpulse.persistence.ai_repository import AIExtractionRepository
from tenderpulse.persistence.models import AIExtractionAttemptRow, Base
from tenderpulse.persistence.repository import ProcurementRepository


class StubGenerator:
    def __init__(self, generated: GeneratedArguments | Exception) -> None:
        self.generated = generated
        self.calls = 0

    def extract_arguments(self, evidence: str) -> GeneratedArguments:
        self.calls += 1
        if isinstance(self.generated, Exception):
            raise self.generated
        return self.generated


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_validated_extraction_is_persisted_and_reused_from_cache(it_notice) -> None:
    session = _session()
    ProcurementRepository(session).apply_records((it_notice,), at=datetime(2026, 8, 8, tzinfo=UTC))
    generator = StubGenerator(
        GeneratedArguments(
            arguments={
                "requirements_status": "found",
                "requirements": [
                    {
                        "text": "Data engineering services are required.",
                        "mandatory": True,
                        "citation": {
                            "field": "description",
                            "quote": "Data engineering",
                        },
                    }
                ],
                "deadlines_status": "unknown",
                "deadlines": [],
                "gaps": [],
            },
            response_model="GigaChat-2:fixture",
        )
    )
    service = AIExtractionService(
        AIExtractionRepository(session),
        generator,
        requested_model="GigaChat-2",
        now=lambda: datetime(2026, 8, 8, 1, tzinfo=UTC),
    )

    first = service.extract(it_notice.source, it_notice.source_record_id)
    session.commit()
    second = service.extract(it_notice.source, it_notice.source_record_id)

    assert first.status is ExtractionStatus.VALIDATED
    assert first.claims is not None
    assert first.claims.requirements[0].citation.quote == "Data engineering"
    assert second == first
    assert generator.calls == 1
    attempts = AIExtractionRepository(session).list_attempts(
        it_notice.source, it_notice.source_record_id
    )
    assert len(attempts) == 1
    assert attempts[0].raw_sha256 == it_notice.evidence.raw_sha256


def test_unsupported_claim_is_rejected_and_recorded(it_notice) -> None:
    session = _session()
    ProcurementRepository(session).apply_records((it_notice,), at=datetime(2026, 8, 8, tzinfo=UTC))
    generator = StubGenerator(
        GeneratedArguments(
            arguments={
                "requirements_status": "found",
                "requirements": [
                    {
                        "text": "ISO 27001 is mandatory.",
                        "mandatory": True,
                        "citation": {
                            "field": "description",
                            "quote": "ISO 27001",
                        },
                    }
                ],
                "deadlines_status": "unknown",
                "deadlines": [],
                "gaps": [],
            },
            response_model="GigaChat-2:fixture",
        )
    )
    service = AIExtractionService(
        AIExtractionRepository(session),
        generator,
        requested_model="GigaChat-2",
        now=lambda: datetime(2026, 8, 8, 1, tzinfo=UTC),
    )

    result = service.extract(it_notice.source, it_notice.source_record_id)
    session.commit()

    assert result.status is ExtractionStatus.REJECTED
    assert result.claims is None
    assert result.error_code == "unsupported_evidence_claim"
    assert (
        AIExtractionRepository(session)
        .list_attempts(it_notice.source, it_notice.source_record_id)[0]
        .status
        == "rejected"
    )


def test_known_gigachat_failure_is_visible_and_does_not_create_claims(it_notice) -> None:
    session = _session()
    ProcurementRepository(session).apply_records((it_notice,), at=datetime(2026, 8, 8, tzinfo=UTC))
    generator = StubGenerator(
        GigaChatError("gigachat_chat_503", "GigaChat chat returned HTTP 503", retryable=True)
    )
    service = AIExtractionService(
        AIExtractionRepository(session),
        generator,
        requested_model="GigaChat-2",
        now=lambda: datetime(2026, 8, 8, 1, tzinfo=UTC),
    )

    result = service.extract(it_notice.source, it_notice.source_record_id)
    session.commit()

    assert result.status is ExtractionStatus.FAILED
    assert result.claims is None
    assert result.retryable is True
    assert result.error_code == "gigachat_chat_503"
    assert ProcurementRepository(session).list_current_records() == (it_notice,)


def test_legacy_validated_attempt_remains_readable_with_explicit_coverage(it_notice) -> None:
    session = _session()
    ProcurementRepository(session).apply_records((it_notice,), at=datetime(2026, 8, 8, tzinfo=UTC))
    repository = AIExtractionRepository(session)
    context = repository.get_current_context(it_notice.source, it_notice.source_record_id)
    assert context is not None
    session.add(
        AIExtractionAttemptRow(
            record_version_id=context.record_version_id,
            provider="gigachat",
            requested_model="GigaChat-2",
            response_model="GigaChat-2:legacy",
            prompt_version="tender-evidence-v1",
            input_sha256="1" * 64,
            output_sha256="2" * 64,
            raw_sha256=it_notice.evidence.raw_sha256,
            status="validated",
            payload={"requirements": [], "deadlines": [], "gaps": []},
            error_code=None,
            error_message=None,
            retryable=False,
            created_at=datetime(2026, 8, 8, 1, tzinfo=UTC),
        )
    )
    session.commit()

    attempt = repository.list_attempts(it_notice.source, it_notice.source_record_id)[0]

    assert attempt.claims is not None
    assert attempt.claims.requirements_status == "unknown"
    assert attempt.claims.deadlines_status == "unknown"
