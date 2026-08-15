from __future__ import annotations

from datetime import UTC, datetime

from tenderpulse.domain.matching import (
    GapCode,
    MatchDecision,
    TenderMatcher,
    current_opportunities,
)
from tenderpulse.domain.models import LifecycleStatus, ProcurementRecord, RecordKind
from tenderpulse.profiles import load_mvp2_legacy_test_profiles as load_demo_profiles


def _profile(slug: str):
    return next(profile for profile in load_demo_profiles() if profile.slug == slug)


def test_four_distinct_demo_profiles_are_seeded() -> None:
    profiles = load_demo_profiles()

    assert {profile.slug for profile in profiles} == {
        "auto-service-moscow",
        "it-russia-integrator",
        "landscaping-moscow",
        "cleaning-moscow",
    }
    assert len({tuple(profile.positive_keywords) for profile in profiles}) == 4


def test_profiles_rank_each_russian_sector_above_unrelated(
    it_notice: ProcurementRecord,
    auto_notice: ProcurementRecord,
    landscaping_notice: ProcurementRecord,
    cleaning_notice: ProcurementRecord,
    unrelated_notice: ProcurementRecord,
) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 8, tzinfo=UTC))
    sectors = (
        ("auto-service-moscow", auto_notice),
        ("it-russia-integrator", it_notice),
        ("landscaping-moscow", landscaping_notice),
        ("cleaning-moscow", cleaning_notice),
    )

    for slug, own_notice in sectors:
        ranked = matcher.rank(_profile(slug), (unrelated_notice, own_notice))
        assert ranked[0].record_source_id == own_notice.source_record_id
        assert ranked[0].decision is MatchDecision.RECOMMENDED


def test_every_positive_reason_is_traceable_to_source_evidence(
    it_notice: ProcurementRecord,
) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 8, tzinfo=UTC))
    it_profile = _profile("it-russia-integrator")

    recommendation = matcher.match(it_profile, it_notice)

    assert recommendation.reasons
    assert all(
        reason.raw_sha256 == it_notice.evidence.raw_sha256 for reason in recommendation.reasons
    )
    assert all(
        reason.source_record_id == it_notice.source_record_id for reason in recommendation.reasons
    )
    assert sum(reason.contribution for reason in recommendation.reasons) == recommendation.score


def test_missing_optional_facts_are_visible_gaps(it_notice: ProcurementRecord) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 8, tzinfo=UTC))
    it_profile = _profile("it-russia-integrator")
    missing = it_notice.model_copy(
        update={
            "deadline_at": None,
            "lots": (
                it_notice.lots[0].model_copy(
                    update={"amount": None, "currency": None, "deadline_at": None}
                ),
            ),
        }
    )

    recommendation = matcher.match(it_profile, missing)

    assert GapCode.UNKNOWN_AMOUNT in recommendation.gaps
    assert GapCode.UNKNOWN_DEADLINE in recommendation.gaps
    assert recommendation.decision is MatchDecision.RECOMMENDED


def test_expired_notice_is_not_recommended(it_notice: ProcurementRecord) -> None:
    matcher = TenderMatcher(now=lambda: datetime(2026, 10, 1, tzinfo=UTC))
    it_profile = _profile("it-russia-integrator")

    recommendation = matcher.match(it_profile, it_notice)

    assert recommendation.decision is MatchDecision.EXPIRED
    assert GapCode.DEADLINE_PASSED in recommendation.gaps


def test_current_opportunities_is_the_single_active_notice_scope(
    it_notice: ProcurementRecord,
) -> None:
    planned = it_notice.model_copy(
        update={"source_record_id": "planned", "lifecycle": LifecycleStatus.PLANNED}
    )
    inactive = it_notice.model_copy(
        update={"source_record_id": "inactive", "lifecycle": LifecycleStatus.CANCELLED}
    )
    award = it_notice.model_copy(update={"source_record_id": "award", "kind": RecordKind.AWARD})

    selected = current_opportunities((inactive, award, planned, it_notice))

    assert [record.source_record_id for record in selected] == [
        "planned",
        it_notice.source_record_id,
    ]
