from __future__ import annotations

from datetime import UTC, datetime

from tenderpulse.domain.matching import GapCode, MatchDecision, TenderMatcher
from tenderpulse.domain.models import ProcurementRecord
from tenderpulse.profiles import load_demo_profiles


def test_exactly_two_distinct_demo_profiles_are_seeded() -> None:
    profiles = load_demo_profiles()

    assert [profile.slug for profile in profiles] == ["it-data-integrator", "medlab-supplier"]
    assert profiles[0].classification_prefixes != profiles[1].classification_prefixes
    assert profiles[0].positive_keywords != profiles[1].positive_keywords


def test_profiles_rank_their_own_sector_above_unrelated(
    it_notice: ProcurementRecord,
    medical_notice: ProcurementRecord,
    unrelated_notice: ProcurementRecord,
) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 8, tzinfo=UTC))
    it_profile, med_profile = load_demo_profiles()

    it_ranked = matcher.rank(it_profile, [medical_notice, unrelated_notice, it_notice])
    med_ranked = matcher.rank(med_profile, [it_notice, unrelated_notice, medical_notice])

    assert it_ranked[0].record_source_id == it_notice.source_record_id
    assert med_ranked[0].record_source_id == medical_notice.source_record_id
    assert it_ranked[0].decision is MatchDecision.RECOMMENDED
    assert med_ranked[0].decision is MatchDecision.RECOMMENDED


def test_every_positive_reason_is_traceable_to_source_evidence(
    it_notice: ProcurementRecord,
) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 8, tzinfo=UTC))
    it_profile = load_demo_profiles()[0]

    recommendation = matcher.match(it_profile, it_notice)

    assert recommendation.reasons
    assert all(
        reason.raw_sha256 == it_notice.evidence.raw_sha256 for reason in recommendation.reasons
    )
    assert all(
        reason.source_record_id == it_notice.source_record_id for reason in recommendation.reasons
    )
    assert sum(reason.contribution for reason in recommendation.reasons) == recommendation.score


def test_missing_optional_facts_are_visible_gaps(
    medical_notice: ProcurementRecord,
) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 8, tzinfo=UTC))
    med_profile = load_demo_profiles()[1]

    recommendation = matcher.match(med_profile, medical_notice)

    assert GapCode.UNKNOWN_AMOUNT in recommendation.gaps
    assert GapCode.UNKNOWN_DEADLINE in recommendation.gaps
    assert recommendation.decision is MatchDecision.RECOMMENDED


def test_expired_notice_is_not_recommended(it_notice: ProcurementRecord) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 10, 1, tzinfo=UTC))
    it_profile = load_demo_profiles()[0]

    recommendation = matcher.match(it_profile, it_notice)

    assert recommendation.decision is MatchDecision.EXPIRED
    assert GapCode.DEADLINE_PASSED in recommendation.gaps
