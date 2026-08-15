from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.history import RecordVersion
from tenderpulse.domain.matching import BlockerCode, MatchDecision, Recommendation
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.outcomes import AwardOutcomeView, CoverageStatus
from tenderpulse.profiles import CompanyProfile

CURRENT_SCOPE = "current_active_or_planned_notices"


class NamedCount(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    count: int = Field(ge=0)


class DecisionCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    recommended: int = Field(ge=0)
    review: int = Field(ge=0)
    not_relevant: int = Field(ge=0)
    expired: int = Field(ge=0)


class CoverageCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    buyer_known: int = Field(ge=0)
    classification_known: int = Field(ge=0)
    geography_known: int = Field(ge=0)
    amount_known: int = Field(ge=0)
    deadline_known: int = Field(ge=0)


class HistoryCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_records: int = Field(ge=0)
    total_versions: int = Field(ge=0)
    changed_records: int = Field(ge=0)


class OutcomeCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    awards: int = Field(ge=0)
    winner_known: int = Field(ge=0)
    amount_known: int = Field(ge=0)


class DiagnosticCounts(BaseModel):
    model_config = ConfigDict(frozen=True)

    geography_rejected: int = Field(ge=0)
    blockers: tuple[NamedCount, ...]
    gaps: tuple[NamedCount, ...]


class DeadlineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_source: SourceCode
    record_source_id: str
    title: str
    deadline_at: datetime
    region_codes: tuple[str, ...]
    decision: MatchDecision


class BudgetSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    known_count: int = Field(ge=0)
    average: Decimal | None = None
    median: Decimal | None = None


class ActivitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    new_records: int = Field(ge=0)
    changed_records: int = Field(ge=0)
    total_versions: int = Field(ge=0)


class ProfileQuality(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: int = Field(ge=0, le=100)
    missing_fields: tuple[str, ...]


class ProductAnalytics(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope: str = CURRENT_SCOPE
    decisions: DecisionCounts
    coverage: CoverageCounts
    sources: tuple[NamedCount, ...]
    categories: tuple[NamedCount, ...]
    geographies: tuple[NamedCount, ...]
    buyers: tuple[NamedCount, ...]
    history: HistoryCounts
    outcomes: OutcomeCounts
    diagnostics: DiagnosticCounts
    nearest_deadlines: tuple[DeadlineItem, ...]
    budget: BudgetSummary
    activity: ActivitySummary
    profile_quality: ProfileQuality


def build_product_analytics(
    *,
    current_records: tuple[ProcurementRecord, ...],
    opportunities: tuple[ProcurementRecord, ...],
    recommendations: list[Recommendation],
    lineages: dict[tuple[SourceCode, str], tuple[RecordVersion, ...]],
    award_outcomes: tuple[AwardOutcomeView, ...],
    profile: CompanyProfile,
    as_of: datetime,
) -> ProductAnalytics:
    opportunity_keys = {record.natural_key for record in opportunities}
    recommendation_keys = {
        f"{item.record_source.value}:{item.record_source_id}" for item in recommendations
    }
    if opportunity_keys != recommendation_keys:
        raise ValueError(
            "analytics recommendations must cover the current opportunity slice exactly"
        )

    decisions = Counter(item.decision for item in recommendations)
    sources = Counter(record.source.value.upper() for record in opportunities)
    categories: Counter[str] = Counter()
    geographies: Counter[str] = Counter()
    buyers: Counter[str] = Counter()
    records_by_key = {record.natural_key: record for record in opportunities}
    for record in opportunities:
        for label in {f"{item.system}:{item.code}" for item in record.classifications}:
            categories[label] += 1
        for region in set(record.region_codes):
            geographies[region] += 1
        if record.buyer_name:
            buyers[record.buyer_name] += 1

    blocker_counts = Counter(
        blocker.value for recommendation in recommendations for blocker in recommendation.blockers
    )
    gap_counts = Counter(
        gap.value for recommendation in recommendations for gap in recommendation.gaps
    )
    decision_by_key = {
        f"{item.record_source.value}:{item.record_source_id}": item.decision
        for item in recommendations
    }
    actionable_keys = {
        f"{item.record_source.value}:{item.record_source_id}"
        for item in recommendations
        if item.decision in {MatchDecision.RECOMMENDED, MatchDecision.REVIEW}
    }
    nearest_deadlines = tuple(
        DeadlineItem(
            record_source=record.source,
            record_source_id=record.source_record_id,
            title=record.title,
            deadline_at=record.deadline_at,
            region_codes=record.region_codes,
            decision=decision_by_key[record.natural_key],
        )
        for record in sorted(
            (
                item
                for item in records_by_key.values()
                if item.natural_key in actionable_keys
                and item.deadline_at is not None
                and item.deadline_at > as_of
            ),
            key=lambda item: (item.deadline_at, item.source_record_id),
        )[:8]
        if record.deadline_at is not None
    )
    budgets = sorted(
        amount
        for record in opportunities
        if (amount := next((lot.amount for lot in record.lots if lot.amount is not None), None))
        is not None
    )
    average = sum(budgets, start=Decimal("0")) / len(budgets) if budgets else None
    median = _median(budgets)
    total_versions = sum(len(versions) for versions in lineages.values())
    changed_records = sum(len(versions) > 1 for versions in lineages.values())

    return ProductAnalytics(
        decisions=DecisionCounts(
            total=len(recommendations),
            recommended=decisions[MatchDecision.RECOMMENDED],
            review=decisions[MatchDecision.REVIEW],
            not_relevant=decisions[MatchDecision.NOT_RELEVANT],
            expired=decisions[MatchDecision.EXPIRED],
        ),
        coverage=CoverageCounts(
            total=len(opportunities),
            buyer_known=sum(record.buyer_name is not None for record in opportunities),
            classification_known=sum(bool(record.classifications) for record in opportunities),
            geography_known=sum(bool(record.region_codes) for record in opportunities),
            amount_known=sum(
                any(lot.amount is not None for lot in record.lots) for record in opportunities
            ),
            deadline_known=sum(record.deadline_at is not None for record in opportunities),
        ),
        sources=_named_counts(sources),
        categories=_named_counts(categories),
        geographies=_named_counts(geographies),
        buyers=_named_counts(buyers),
        history=HistoryCounts(
            current_records=len(current_records),
            total_versions=sum(len(versions) for versions in lineages.values()),
            changed_records=sum(len(versions) > 1 for versions in lineages.values()),
        ),
        outcomes=OutcomeCounts(
            awards=len(award_outcomes),
            winner_known=sum(
                outcome.winner_status is CoverageStatus.FOUND for outcome in award_outcomes
            ),
            amount_known=sum(
                outcome.amount_status is CoverageStatus.FOUND for outcome in award_outcomes
            ),
        ),
        diagnostics=DiagnosticCounts(
            geography_rejected=sum(
                any(
                    blocker
                    in {
                        BlockerCode.GEOGRAPHY_OUT_OF_SCOPE,
                        BlockerCode.GEOGRAPHY_EXCLUDED,
                    }
                    for blocker in recommendation.blockers
                )
                for recommendation in recommendations
            ),
            blockers=_named_counts(blocker_counts),
            gaps=_named_counts(gap_counts),
        ),
        nearest_deadlines=nearest_deadlines,
        budget=BudgetSummary(
            known_count=len(budgets),
            average=average,
            median=median,
        ),
        activity=ActivitySummary(
            new_records=sum(len(versions) == 1 for versions in lineages.values()),
            changed_records=changed_records,
            total_versions=total_versions,
        ),
        profile_quality=_profile_quality(profile),
    )


def _named_counts(counter: Counter[str]) -> tuple[NamedCount, ...]:
    return tuple(
        NamedCount(label=label, count=count)
        for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    )


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def _profile_quality(profile: CompanyProfile) -> ProfileQuality:
    checks = {
        "description": bool(profile.description),
        "services": bool(profile.services),
        "capabilities": bool(profile.capabilities),
        "positive_keywords": bool(profile.positive_keywords),
        "negative_keywords": bool(profile.negative_keywords),
        "classification_prefixes": bool(profile.classification_prefixes),
        "customer_types": bool(profile.customer_types),
        "base_region": profile.base_region is not None,
        "service_coverage": bool(profile.service_regions) or profile.nationwide,
        "delivery_mode": profile.delivery_mode is not ServiceDeliveryMode.UNKNOWN,
        "participation_constraints": bool(profile.participation_constraints),
        "budget_range": profile.min_amount is not None and profile.max_amount is not None,
    }
    missing = tuple(field for field, complete in checks.items() if not complete)
    return ProfileQuality(
        score=round((len(checks) - len(missing)) / len(checks) * 100),
        missing_fields=missing,
    )


__all__ = ["ProductAnalytics", "build_product_analytics"]
