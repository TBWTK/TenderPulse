from __future__ import annotations

from datetime import UTC, datetime

import pytest
from conftest import build_record
from pydantic import ValidationError

from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.matching import BlockerCode, GapCode, MatchDecision, TenderMatcher
from tenderpulse.domain.models import ClassificationCode, ProcurementRecord, SourceCode
from tenderpulse.profiles import load_mvp2_legacy_test_profiles as load_demo_profiles


def _profile(slug: str):
    return next(profile for profile in load_demo_profiles() if profile.slug == slug)


def _russian_notice(
    *,
    source_record_id: str,
    title: str,
    description: str,
    region_codes: tuple[str, ...],
    delivery_mode: ServiceDeliveryMode,
    classification_code: str = "50110000",
) -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id=source_record_id,
        title=title,
        description=description,
        countries=("RU",),
        codes=(ClassificationCode(system="CPV", code=classification_code),),
        region_codes=region_codes,
        delivery_location="Россия",
        delivery_mode=delivery_mode,
        currency="RUB",
    )


def test_canonical_record_rejects_non_iso_russian_region() -> None:
    with pytest.raises(ValidationError, match="ISO 3166-2 Russian region"):
        _russian_notice(
            source_record_id="bad-region",
            title="Ремонт автомобиля",
            description="Техническое обслуживание автомобиля",
            region_codes=("МОСКВА",),
            delivery_mode=ServiceDeliveryMode.ONSITE,
        )


def test_moscow_onsite_auto_service_is_recommended() -> None:
    notice = _russian_notice(
        source_record_id="auto-moscow",
        title="Техническое обслуживание и ремонт автомобилей",
        description="Ремонт автотранспорта заказчика в Москве",
        region_codes=("RU-MOW",),
        delivery_mode=ServiceDeliveryMode.ONSITE,
    )

    recommendation = TenderMatcher(now=lambda: datetime(2026, 8, 15, tzinfo=UTC)).match(
        _profile("auto-service-moscow"), notice
    )

    assert recommendation.decision is MatchDecision.RECOMMENDED
    assert any(reason.code == "geography_service_region" for reason in recommendation.reasons)
    assert recommendation.blockers == ()


def test_moscow_onsite_auto_service_rejects_kamchatka_without_contractors() -> None:
    notice = _russian_notice(
        source_record_id="auto-kamchatka",
        title="Техническое обслуживание и ремонт автомобилей",
        description="Ремонт автотранспорта заказчика в Камчатском крае",
        region_codes=("RU-KAM",),
        delivery_mode=ServiceDeliveryMode.ONSITE,
    )

    recommendation = TenderMatcher(now=lambda: datetime(2026, 8, 15, tzinfo=UTC)).match(
        _profile("auto-service-moscow"), notice
    )

    assert recommendation.decision is MatchDecision.NOT_RELEVANT
    assert BlockerCode.GEOGRAPHY_OUT_OF_SCOPE in recommendation.blockers


def test_contractor_policy_makes_remote_region_reviewable_with_evidence() -> None:
    notice = _russian_notice(
        source_record_id="auto-kamchatka-contractor",
        title="Техническое обслуживание и ремонт автомобилей",
        description="Ремонт автотранспорта заказчика в Камчатском крае",
        region_codes=("RU-KAM",),
        delivery_mode=ServiceDeliveryMode.ONSITE,
    )
    profile = _profile("auto-service-moscow").model_copy(
        update={"version": 2, "contractors_allowed": True}
    )

    recommendation = TenderMatcher(now=lambda: datetime(2026, 8, 15, tzinfo=UTC)).match(
        profile, notice
    )

    assert recommendation.decision is MatchDecision.REVIEW
    assert any(reason.code == "geography_contractor_coverage" for reason in recommendation.reasons)
    assert recommendation.blockers == ()


def test_remote_it_is_recommended_for_vladivostok() -> None:
    notice = _russian_notice(
        source_record_id="it-vladivostok",
        title="Разработка информационной системы",
        description="Разработка программного обеспечения и интеграция данных удаленно",
        region_codes=("RU-PRI",),
        delivery_mode=ServiceDeliveryMode.REMOTE,
        classification_code="72200000",
    )

    recommendation = TenderMatcher(now=lambda: datetime(2026, 8, 15, tzinfo=UTC)).match(
        _profile("it-russia-integrator"), notice
    )

    assert recommendation.decision is MatchDecision.RECOMMENDED
    assert any(reason.code == "geography_nationwide_remote" for reason in recommendation.reasons)


def test_unknown_location_is_explicit_and_requires_review() -> None:
    notice = _russian_notice(
        source_record_id="auto-unknown-region",
        title="Техническое обслуживание и ремонт автомобилей",
        description="Ремонт автотранспорта заказчика",
        region_codes=(),
        delivery_mode=ServiceDeliveryMode.ONSITE,
    )

    recommendation = TenderMatcher(now=lambda: datetime(2026, 8, 15, tzinfo=UTC)).match(
        _profile("auto-service-moscow"), notice
    )

    assert recommendation.decision is MatchDecision.REVIEW
    assert GapCode.UNKNOWN_LOCATION in recommendation.gaps
    assert recommendation.blockers == ()


def test_negative_keyword_is_an_explicit_business_blocker() -> None:
    notice = _russian_notice(
        source_record_id="auto-lease",
        title="Строительство автомобильных дорог",
        description="Строительство автомобильных дорог без ремонта транспорта",
        region_codes=("RU-MOW",),
        delivery_mode=ServiceDeliveryMode.ONSITE,
    )

    recommendation = TenderMatcher(now=lambda: datetime(2026, 8, 15, tzinfo=UTC)).match(
        _profile("auto-service-moscow"), notice
    )

    assert recommendation.decision is MatchDecision.NOT_RELEVANT
    assert BlockerCode.NEGATIVE_KEYWORD in recommendation.blockers
