from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from tenderpulse.domain.geography import GeographyStatus, assess_geography
from tenderpulse.domain.models import (
    LifecycleStatus,
    ProcurementRecord,
    RecordKind,
    SourceCode,
)
from tenderpulse.profiles import CompanyProfile
from tenderpulse.source_policy import current_product_records


class MatchDecision(StrEnum):
    RECOMMENDED = "recommended"
    REVIEW = "review"
    NOT_RELEVANT = "not_relevant"
    EXPIRED = "expired"


class GapCode(StrEnum):
    UNKNOWN_AMOUNT = "unknown_amount"
    UNKNOWN_DEADLINE = "unknown_deadline"
    UNKNOWN_LOCATION = "unknown_location"
    QUALIFICATION_REVIEW_REQUIRED = "qualification_review_required"
    DEADLINE_PASSED = "deadline_passed"


class BlockerCode(StrEnum):
    NEGATIVE_KEYWORD = "negative_keyword"
    GEOGRAPHY_OUT_OF_SCOPE = "geography_out_of_scope"
    GEOGRAPHY_EXCLUDED = "geography_excluded"
    AMOUNT_OUT_OF_RANGE = "amount_out_of_range"


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
    blockers: tuple[BlockerCode, ...] = ()


def current_opportunities(
    records: Iterable[ProcurementRecord],
) -> tuple[ProcurementRecord, ...]:
    """Return the canonical matching scope: current active or planned notices."""
    return tuple(
        record
        for record in current_product_records(records)
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
        blockers: list[BlockerCode] = []

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

        negative_matches = [
            keyword
            for keyword in profile.negative_keywords
            if self._contains(text, keyword.casefold())
        ]
        if negative_matches:
            blockers.append(BlockerCode.NEGATIVE_KEYWORD)

        geography = assess_geography(
            profile_delivery_mode=profile.delivery_mode,
            service_regions=profile.service_regions,
            nationwide=profile.nationwide,
            travel_allowed=profile.travel_allowed,
            contractors_allowed=profile.contractors_allowed,
            excluded_regions=profile.excluded_regions,
            notice_delivery_mode=record.delivery_mode,
            notice_regions=record.region_codes,
        )
        if geography.status is GeographyStatus.UNKNOWN:
            gaps.append(GapCode.UNKNOWN_LOCATION)
        elif geography.status is GeographyStatus.SERVICE_REGION:
            add_reason("geography_service_region", "0.10", geography.region_codes)
        elif geography.status is GeographyStatus.NATIONWIDE_REMOTE:
            add_reason("geography_nationwide_remote", "0.10", geography.region_codes)
        elif geography.status is GeographyStatus.CONTRACTOR_COVERAGE:
            add_reason("geography_contractor_coverage", "0.05", geography.region_codes)
        elif geography.status is GeographyStatus.TRAVEL_COVERAGE:
            add_reason("geography_travel_coverage", "0.05", geography.region_codes)
        elif geography.status is GeographyStatus.EXCLUDED:
            blockers.append(BlockerCode.GEOGRAPHY_EXCLUDED)
        else:
            blockers.append(BlockerCode.GEOGRAPHY_OUT_OF_SCOPE)

        amounts = [lot.amount for lot in record.lots if lot.amount is not None]
        has_unknown_amount = any(lot.amount is None for lot in record.lots)
        budget_bounded = profile.min_amount is not None or profile.max_amount is not None
        if not amounts:
            gaps.append(GapCode.UNKNOWN_AMOUNT)
        else:
            accepted_amounts = [amount for amount in amounts if profile.accepts_amount(amount)]
            if accepted_amounts:
                add_reason("budget", "0.05", (str(amount) for amount in accepted_amounts))
                if profile.review_above_amount is not None and all(
                    amount > profile.review_above_amount for amount in accepted_amounts
                ):
                    gaps.append(GapCode.QUALIFICATION_REVIEW_REQUIRED)
            elif has_unknown_amount:
                gaps.append(GapCode.UNKNOWN_AMOUNT)
            elif budget_bounded:
                blockers.append(BlockerCode.AMOUNT_OUT_OF_RANGE)

        if record.deadline_at is None:
            gaps.append(GapCode.UNKNOWN_DEADLINE)
        elif record.deadline_at <= self._now():
            gaps.append(GapCode.DEADLINE_PASSED)

        score = sum((reason.contribution for reason in reasons), start=Decimal("0"))
        if GapCode.DEADLINE_PASSED in gaps:
            decision = MatchDecision.EXPIRED
        elif blockers:
            decision = MatchDecision.NOT_RELEVANT
        elif score >= Decimal("0.55"):
            decision = (
                MatchDecision.REVIEW
                if geography.status
                in {
                    GeographyStatus.CONTRACTOR_COVERAGE,
                    GeographyStatus.TRAVEL_COVERAGE,
                    GeographyStatus.UNKNOWN,
                }
                or (budget_bounded and GapCode.UNKNOWN_AMOUNT in gaps)
                or GapCode.QUALIFICATION_REVIEW_REQUIRED in gaps
                else MatchDecision.RECOMMENDED
            )
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
            blockers=tuple(dict.fromkeys(blockers)),
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
