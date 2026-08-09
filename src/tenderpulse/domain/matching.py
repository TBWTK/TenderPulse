from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from tenderpulse.domain.models import (
    LifecycleStatus,
    ProcurementRecord,
    RecordKind,
    SourceCode,
)
from tenderpulse.profiles import CompanyProfile


class MatchDecision(StrEnum):
    RECOMMENDED = "recommended"
    REVIEW = "review"
    NOT_RELEVANT = "not_relevant"
    EXPIRED = "expired"


class GapCode(StrEnum):
    UNKNOWN_AMOUNT = "unknown_amount"
    UNKNOWN_DEADLINE = "unknown_deadline"
    UNKNOWN_LOCATION = "unknown_location"
    DEADLINE_PASSED = "deadline_passed"


class MatchReason(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    contribution: Decimal
    matched_values: tuple[str, ...]
    source_record_id: str
    raw_sha256: str


class Recommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_slug: str
    record_source: SourceCode
    record_source_id: str
    score: Decimal
    decision: MatchDecision
    reasons: tuple[MatchReason, ...]
    gaps: tuple[GapCode, ...]


def current_opportunities(
    records: Iterable[ProcurementRecord],
) -> tuple[ProcurementRecord, ...]:
    """Return the canonical matching scope: current active or planned notices."""
    return tuple(
        record
        for record in records
        if record.kind is RecordKind.NOTICE
        and record.lifecycle in {LifecycleStatus.ACTIVE, LifecycleStatus.PLANNED}
    )


class TenderMatcher:
    def __init__(self, *, now: Callable[[], datetime]) -> None:
        self._now = now

    def rank(
        self,
        profile: CompanyProfile,
        records: Iterable[ProcurementRecord],
    ) -> list[Recommendation]:
        recommendations = [self.match(profile, record) for record in records]
        return sorted(recommendations, key=lambda item: (-item.score, item.record_source_id))

    def match(self, profile: CompanyProfile, record: ProcurementRecord) -> Recommendation:
        reasons: list[MatchReason] = []
        gaps: list[GapCode] = []

        def add_reason(code: str, contribution: str, values: Iterable[str]) -> None:
            matched = tuple(dict.fromkeys(values))
            if not matched:
                return
            reasons.append(
                MatchReason(
                    code=code,
                    contribution=Decimal(contribution),
                    matched_values=matched,
                    source_record_id=record.source_record_id,
                    raw_sha256=record.evidence.raw_sha256,
                )
            )

        code_matches = self._classification_matches(profile, record)
        add_reason("classification", "0.55", code_matches)

        text = f"{record.title} {record.description}".casefold()
        keyword_matches = [
            keyword
            for keyword in profile.positive_keywords
            if self._contains(text, keyword.casefold())
        ]
        if keyword_matches:
            contribution = min(Decimal("0.30"), Decimal("0.10") * len(keyword_matches))
            add_reason("keywords", str(contribution), keyword_matches)

        if record.countries:
            country_matches = sorted(set(record.countries) & set(profile.countries))
            add_reason("geography", "0.10", country_matches)
        else:
            gaps.append(GapCode.UNKNOWN_LOCATION)

        amounts = [lot.amount for lot in record.lots if lot.amount is not None]
        if not amounts:
            gaps.append(GapCode.UNKNOWN_AMOUNT)
        elif any(profile.accepts_amount(amount) for amount in amounts):
            add_reason("budget", "0.05", (str(amount) for amount in amounts))

        if record.deadline_at is None:
            gaps.append(GapCode.UNKNOWN_DEADLINE)
        elif record.deadline_at <= self._now():
            gaps.append(GapCode.DEADLINE_PASSED)

        score = sum((reason.contribution for reason in reasons), start=Decimal("0"))
        if GapCode.DEADLINE_PASSED in gaps:
            decision = MatchDecision.EXPIRED
        elif score >= Decimal("0.55"):
            decision = MatchDecision.RECOMMENDED
        elif score >= Decimal("0.30"):
            decision = MatchDecision.REVIEW
        else:
            decision = MatchDecision.NOT_RELEVANT

        return Recommendation(
            profile_slug=profile.slug,
            record_source=record.source,
            record_source_id=record.source_record_id,
            score=score,
            decision=decision,
            reasons=tuple(reasons),
            gaps=tuple(dict.fromkeys(gaps)),
        )

    @staticmethod
    def _contains(text: str, keyword: str) -> bool:
        if " " in keyword or not keyword.isascii():
            return keyword in text
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

    @staticmethod
    def _classification_matches(
        profile: CompanyProfile,
        record: ProcurementRecord,
    ) -> list[str]:
        matches: list[str] = []
        for classification in record.classifications:
            prefixes = profile.classification_prefixes.get(classification.system, ())
            if any(classification.code.startswith(prefix) for prefix in prefixes):
                matches.append(f"{classification.system}:{classification.code}")
        return matches
