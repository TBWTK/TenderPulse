from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from conftest import build_record

from tenderpulse.api import DIAGNOSTIC_LABELS
from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.matching import BlockerCode, GapCode, MatchDecision, TenderMatcher
from tenderpulse.domain.models import ClassificationCode, ProcurementRecord, SourceCode
from tenderpulse.profiles import load_demo_profiles


def test_mvp21_demo_authority_contains_only_cleaning_and_office_supply() -> None:
    profiles = load_demo_profiles()

    assert [profile.slug for profile in profiles] == [
        "cleaning-moscow",
        "office-supply-moscow",
    ]
    assert "канцеляр" in " ".join(profiles[1].positive_keywords)
    assert profiles[0].delivery_mode.value == "onsite"


def test_cleaning_pilot_profile_matches_confirmed_facts_and_preserves_unknowns() -> None:
    cleaning = load_demo_profiles()[0]

    assert cleaning.name == "Чистая территория"
    assert cleaning.base_region == "RU-MOW"
    assert cleaning.service_regions == ("RU-MOW", "RU-MOS")
    assert cleaning.contractors_allowed is True
    assert cleaning.min_amount == Decimal("500000")
    assert cleaning.max_amount == Decimal("25000000")
    assert cleaning.review_above_amount == Decimal("1000000")
    assert "9061" in cleaning.classification_prefixes["CPV"]
    constraints = " ".join(cleaning.participation_constraints).casefold()
    assert "unknown" in constraints
    assert "документац" in constraints
    assert "лиценз" in constraints


def _cleaning_notice(
    *,
    source_record_id: str,
    title: str,
    code: str,
    amount: Decimal | None = Decimal("2000000"),
    region: str = "RU-MOW",
) -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id=source_record_id,
        title=title,
        description=title,
        codes=(ClassificationCode(system="CPV", code=code),),
        countries=("RU",),
        region_codes=(region,),
        delivery_location="Россия",
        delivery_mode=ServiceDeliveryMode.ONSITE,
        amount=amount,
        currency="RUB" if amount is not None else None,
    )


@pytest.mark.parametrize(
    ("source_record_id", "title", "code", "amount", "expected"),
    [
        (
            "clean-office",
            "Ежедневная уборка офисных помещений",
            "90919200",
            Decimal("500000"),
            MatchDecision.RECOMMENDED,
        ),
        (
            "clean-yard",
            "Содержание и уборка дворовых территорий",
            "90610000",
            Decimal("900000"),
            MatchDecision.RECOMMENDED,
        ),
        (
            "clean-windows",
            "Генеральная уборка и мойка окон",
            "90910000",
            Decimal("1000000"),
            MatchDecision.RECOMMENDED,
        ),
        (
            "clean-building",
            "Комплексная уборка административного здания",
            "90910000",
            Decimal("8000000"),
            MatchDecision.REVIEW,
        ),
        (
            "clean-snow",
            "Уборка помещений и зимнее содержание нескольких объектов",
            "90620000",
            Decimal("25000000"),
            MatchDecision.REVIEW,
        ),
    ],
)
def test_cleaning_pilot_positive_scenarios_follow_qualification_review_threshold(
    source_record_id: str,
    title: str,
    code: str,
    amount: Decimal,
    expected: MatchDecision,
) -> None:
    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(
        load_demo_profiles()[0],
        _cleaning_notice(
            source_record_id=source_record_id,
            title=title,
            code=code,
            amount=amount,
        ),
    )

    assert result.decision is expected
    assert result.blockers == ()
    if amount > Decimal("1000000"):
        assert GapCode.QUALIFICATION_REVIEW_REQUIRED in result.gaps


@pytest.mark.parametrize(
    ("source_record_id", "title", "code"),
    [
        ("supply-only", "Поставка моющих средств и уборочного инвентаря", "39800000"),
        ("medical-waste", "Вывоз и обезвреживание медицинских отходов", "90524000"),
        ("landscaping", "Озеленение территорий и высадка деревьев", "45112710"),
        ("construction", "Капитальный ремонт помещений", "45000000"),
        ("pest-control", "Дезинсекция и дератизация помещений", "90923000"),
    ],
)
def test_cleaning_pilot_excluded_scenarios_are_explicitly_blocked(
    source_record_id: str,
    title: str,
    code: str,
) -> None:
    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(
        load_demo_profiles()[0],
        _cleaning_notice(source_record_id=source_record_id, title=title, code=code),
    )

    assert result.decision is MatchDecision.NOT_RELEVANT
    assert BlockerCode.NEGATIVE_KEYWORD in result.blockers


def test_cleaning_pilot_outside_service_regions_requires_contractor_review() -> None:
    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(
        load_demo_profiles()[0],
        _cleaning_notice(
            source_record_id="clean-kamchatka",
            title="Комплексная уборка помещений",
            code="90910000",
            region="RU-KAM",
        ),
    )

    assert result.decision is MatchDecision.REVIEW
    assert result.blockers == ()
    assert any(reason.code == "geography_contractor_coverage" for reason in result.reasons)


@pytest.mark.parametrize("amount", [Decimal("499999.99"), Decimal("25000000.01")])
def test_cleaning_pilot_known_out_of_range_budget_is_blocked(amount: Decimal) -> None:
    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(
        load_demo_profiles()[0],
        _cleaning_notice(
            source_record_id=f"clean-budget-{amount}",
            title="Комплексная уборка помещений",
            code="90910000",
            amount=amount,
        ),
    )

    assert result.decision is MatchDecision.NOT_RELEVANT
    assert BlockerCode.AMOUNT_OUT_OF_RANGE in result.blockers


def test_cleaning_pilot_unknown_budget_is_review_not_a_guessed_recommendation() -> None:
    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(
        load_demo_profiles()[0],
        _cleaning_notice(
            source_record_id="clean-budget-unknown",
            title="Комплексная уборка помещений",
            code="90910000",
            amount=None,
        ),
    )

    assert result.decision is MatchDecision.REVIEW
    assert GapCode.UNKNOWN_AMOUNT in result.gaps
    assert result.blockers == ()
    assert DIAGNOSTIC_LABELS["amount_out_of_range"] == "сумма вне диапазона компании"
    assert DIAGNOSTIC_LABELS["qualification_review_required"] == (
        "нужно подтвердить квалификацию и опыт"
    )


def test_cleaning_pilot_mixed_lots_keep_only_proven_eligible_amounts() -> None:
    profile = load_demo_profiles()[0]
    record = _cleaning_notice(
        source_record_id="clean-mixed-lots",
        title="Комплексная уборка помещений по отдельным лотам",
        code="90910000",
        amount=Decimal("30000000"),
    )
    eligible = record.lots[0].model_copy(
        update={"source_lot_id": "LOT-2", "amount": Decimal("600000")}
    )
    mixed = record.model_copy(update={"lots": (record.lots[0], eligible)})

    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(profile, mixed)

    assert result.decision is MatchDecision.RECOMMENDED
    assert result.blockers == ()
    budget_reason = next(reason for reason in result.reasons if reason.code == "budget")
    assert budget_reason.matched_values == ("600000",)


def test_cleaning_pilot_partial_unknown_lots_require_review_instead_of_budget_block() -> None:
    profile = load_demo_profiles()[0]
    record = _cleaning_notice(
        source_record_id="clean-partial-budget",
        title="Комплексная уборка помещений по отдельным лотам",
        code="90910000",
        amount=Decimal("30000000"),
    )
    unknown = record.lots[0].model_copy(
        update={"source_lot_id": "LOT-2", "amount": None, "currency": None}
    )
    partial = record.model_copy(update={"lots": (record.lots[0], unknown)})

    result = TenderMatcher(now=lambda: datetime(2026, 8, 16, tzinfo=UTC)).match(profile, partial)

    assert result.decision is MatchDecision.REVIEW
    assert result.blockers == ()
    assert GapCode.UNKNOWN_AMOUNT in result.gaps


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
