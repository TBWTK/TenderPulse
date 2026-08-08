from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from tenderpulse.ai.evidence import (
    PROMPT_VERSION,
    EvidenceValidationError,
    build_evidence_input,
    validate_extraction_arguments,
)
from tenderpulse.ai.gigachat import GeneratedArguments, GigaChatError
from tenderpulse.ai.models import ExtractionOutcome, ExtractionStatus
from tenderpulse.domain.models import SourceCode
from tenderpulse.persistence.ai_repository import AIExtractionRepository, CurrentRecordContext

PROVIDER = "gigachat"


class EvidenceGenerator(Protocol):
    def extract_arguments(self, evidence: str) -> GeneratedArguments: ...


class AIExtractionService:
    def __init__(
        self,
        repository: AIExtractionRepository,
        generator: EvidenceGenerator,
        *,
        requested_model: str,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._requested_model = requested_model
        self._now = now

    def extract(self, source: SourceCode, source_record_id: str) -> ExtractionOutcome:
        context = self._repository.get_current_context(source, source_record_id)
        if context is None:
            raise LookupError(f"procurement record not found: {source.value}:{source_record_id}")
        evidence_input = build_evidence_input(context.record)
        cached = self._repository.find_validated(
            context,
            provider=PROVIDER,
            requested_model=self._requested_model,
            prompt_version=PROMPT_VERSION,
            input_sha256=evidence_input.input_sha256,
        )
        if cached is not None:
            return cached

        try:
            generated = self._generator.extract_arguments(evidence_input.render())
        except GigaChatError as error:
            return self._record_failure(context, evidence_input.input_sha256, error)

        output_sha256 = hashlib.sha256(
            json.dumps(
                generated.arguments,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        try:
            claims = validate_extraction_arguments(evidence_input, generated.arguments)
        except EvidenceValidationError as error:
            return self._repository.add_attempt(
                context,
                provider=PROVIDER,
                requested_model=self._requested_model,
                response_model=generated.response_model,
                prompt_version=PROMPT_VERSION,
                input_sha256=evidence_input.input_sha256,
                output_sha256=output_sha256,
                status=ExtractionStatus.REJECTED,
                claims=None,
                error_code="unsupported_evidence_claim",
                error_message=str(error),
                retryable=False,
                created_at=self._now(),
            )
        return self._repository.add_attempt(
            context,
            provider=PROVIDER,
            requested_model=self._requested_model,
            response_model=generated.response_model,
            prompt_version=PROMPT_VERSION,
            input_sha256=evidence_input.input_sha256,
            output_sha256=output_sha256,
            status=ExtractionStatus.VALIDATED,
            claims=claims,
            error_code=None,
            error_message=None,
            retryable=False,
            created_at=self._now(),
        )

    def _record_failure(
        self,
        context: CurrentRecordContext,
        input_sha256: str,
        error: GigaChatError,
    ) -> ExtractionOutcome:
        return self._repository.add_attempt(
            context,
            provider=PROVIDER,
            requested_model=self._requested_model,
            response_model=None,
            prompt_version=PROMPT_VERSION,
            input_sha256=input_sha256,
            output_sha256=None,
            status=ExtractionStatus.FAILED,
            claims=None,
            error_code=error.code,
            error_message=str(error),
            retryable=error.retryable,
            created_at=self._now(),
        )


__all__ = ["AIExtractionService", "ExtractionStatus"]
