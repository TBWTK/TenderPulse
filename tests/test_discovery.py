from __future__ import annotations

import pytest

from tenderpulse.discovery import (
    DISCOVERY_STRATEGY_VERSION,
    MAX_DISCOVERY_QUERIES,
    build_eis_discovery_plan,
)
from tenderpulse.profiles import load_demo_profiles


def test_discovery_plan_uses_three_deduplicated_service_phrases_per_profile() -> None:
    cleaning, office = load_demo_profiles()

    plan = build_eis_discovery_plan((cleaning, office))

    assert [(item.profile_slug, item.profile_version, item.search_string) for item in plan] == [
        ("cleaning-moscow", 1, "уборка помещений"),
        ("cleaning-moscow", 1, "уборка дворов и прилегающих территорий"),
        ("cleaning-moscow", 1, "поддержание чистоты и санитарное содержание"),
        ("office-supply-moscow", 1, "поставка офисной мебели"),
        ("office-supply-moscow", 1, "поставка канцелярских товаров и бумаги"),
        ("office-supply-moscow", 1, "поставка принтеров и многофункциональных устройств"),
    ]
    assert {item.strategy_version for item in plan} == {DISCOVERY_STRATEGY_VERSION}


def test_discovery_plan_falls_back_to_keywords_without_guessing_new_terms() -> None:
    profile = load_demo_profiles()[0].model_copy(
        update={"services": (), "positive_keywords": ("  Уборка помещений  ", "Клининг")}
    )

    plan = build_eis_discovery_plan((profile,))

    assert [item.search_string for item in plan] == ["Уборка помещений", "Клининг"]


def test_discovery_plan_fails_loud_when_global_bound_is_exceeded() -> None:
    template = load_demo_profiles()[0]
    profiles = tuple(
        template.model_copy(update={"slug": f"profile-{index}"})
        for index in range(MAX_DISCOVERY_QUERIES // 3 + 1)
    )

    with pytest.raises(RuntimeError, match="discovery query limit"):
        build_eis_discovery_plan(profiles)
