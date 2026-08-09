from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from tenderpulse.domain.history import RecordVersion
from tenderpulse.domain.matching import MatchDecision, Recommendation
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.outcomes import AwardOutcomeView, CoverageStatus

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


def build_product_analytics(
    *,
    current_records: tuple[ProcurementRecord, ...],
    opportunities: tuple[ProcurementRecord, ...],
    recommendations: list[Recommendation],
    lineages: dict[tuple[SourceCode, str], tuple[RecordVersion, ...]],
    award_outcomes: tuple[AwardOutcomeView, ...],
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
    for record in opportunities:
        for label in {f"{item.system}:{item.code}" for item in record.classifications}:
            categories[label] += 1
        for country in set(record.countries):
            geographies[country] += 1
        if record.buyer_name:
            buyers[record.buyer_name] += 1

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
            geography_known=sum(bool(record.countries) for record in opportunities),
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
    )


def _named_counts(counter: Counter[str]) -> tuple[NamedCount, ...]:
    return tuple(
        NamedCount(label=label, count=count)
        for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    )


__all__ = ["ProductAnalytics", "build_product_analytics"]
