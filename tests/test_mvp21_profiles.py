from __future__ import annotations

from datetime import UTC, datetime

from tenderpulse.domain.matching import TenderMatcher
from tenderpulse.profiles import load_demo_profiles


def test_mvp21_demo_authority_contains_only_cleaning_and_office_supply() -> None:
    profiles = load_demo_profiles()

    assert [profile.slug for profile in profiles] == [
        "cleaning-moscow",
        "office-supply-moscow",
    ]
    assert "канцеляр" in " ".join(profiles[1].positive_keywords)
    assert profiles[0].delivery_mode.value == "onsite"


def test_office_profile_accepts_office_goods_and_rejects_software(
    office_notice,
    it_notice,
) -> None:
    office = load_demo_profiles()[1]
    matcher = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC))

    office_result = matcher.match(office, office_notice)
    software_result = matcher.match(office, it_notice)

    assert office_result.decision.value == "recommended"
    assert software_result.decision.value == "not_relevant"
