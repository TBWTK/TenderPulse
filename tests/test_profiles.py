from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from tenderpulse.profiles import CompanyProfile, ServiceDeliveryMode, load_demo_profiles


def _profile_payload() -> dict[str, object]:
    return {
        "slug": "company-profile",
        "version": 1,
        "name": "  Example   Company  ",
        "description": "  Разработка   корпоративных систем  ",
        "services": [" Web-разработка ", "web-разработка", "Интеграция"],
        "capabilities": ["  Cloud security  ", "cloud security", "Data platforms"],
        "positive_keywords": [" CLOUD ", "cloud", " data   mesh "],
        "negative_keywords": [" поставка компьютеров ", "ПОСТАВКА КОМПЬЮТЕРОВ"],
        "classification_prefixes": {
            "cpv": ["72-00", "7200"],
            "okpd2": ["62.01"],
            "psc": ["d3"],
        },
        "countries": ["de", "DE", "us"],
        "customer_types": [" Государственные заказчики ", "государственные заказчики"],
        "base_region": "ru-mow",
        "service_regions": ["ru-mow", "RU-MOS", "ru-mow"],
        "delivery_mode": "hybrid",
        "nationwide": False,
        "travel_allowed": True,
        "contractors_allowed": False,
        "excluded_regions": ["ru-kam"],
        "participation_constraints": [" Требуется выезд инженера ", "требуется выезд инженера"],
        "min_amount": "100000",
        "max_amount": "5000000",
    }


def test_company_profile_normalizes_and_deduplicates_user_input() -> None:
    profile = CompanyProfile.model_validate(_profile_payload())

    assert profile.name == "Example Company"
    assert profile.description == "Разработка корпоративных систем"
    assert profile.services == ("Web-разработка", "Интеграция")
    assert profile.capabilities == ("Cloud security", "Data platforms")
    assert profile.positive_keywords == ("cloud", "data mesh")
    assert profile.negative_keywords == ("поставка компьютеров",)
    assert profile.classification_prefixes == {
        "CPV": ("7200",),
        "OKPD2": ("62.01",),
        "PSC": ("D3",),
    }
    assert profile.countries == ("DE", "US")
    assert profile.customer_types == ("Государственные заказчики",)
    assert profile.base_region == "RU-MOW"
    assert profile.service_regions == ("RU-MOW", "RU-MOS")
    assert profile.delivery_mode is ServiceDeliveryMode.HYBRID
    assert profile.nationwide is False
    assert profile.travel_allowed is True
    assert profile.contractors_allowed is False
    assert profile.excluded_regions == ("RU-KAM",)
    assert profile.participation_constraints == ("Требуется выезд инженера",)
    assert profile.min_amount == Decimal("100000")
    assert profile.max_amount == Decimal("5000000")


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"capabilities": []}, "capabilities"),
        ({"positive_keywords": ["  "]}, "positive_keywords"),
        ({"classification_prefixes": {"UNSUPPORTED": ["1"]}}, "classification system"),
        ({"classification_prefixes": {"CPV": ["  "]}}, "classification prefix"),
        ({"countries": ["Germany"]}, "ISO 3166-1 alpha-2"),
        ({"base_region": "MOSCOW"}, "ISO 3166-2 Russian region"),
        (
            {"service_regions": ["RU-MOW"], "excluded_regions": ["RU-MOW"]},
            "service_regions and excluded_regions",
        ),
    ],
)
def test_company_profile_rejects_unusable_matching_input(
    updates: dict[str, object],
    message: str,
) -> None:
    payload = _profile_payload()
    payload.update(updates)

    with pytest.raises(ValidationError, match=message):
        CompanyProfile.model_validate(payload)


def test_two_mvp21_profiles_cover_cleaning_and_office_supply() -> None:
    profiles = load_demo_profiles()

    assert [profile.slug for profile in profiles] == [
        "cleaning-moscow",
        "office-supply-moscow",
    ]
    assert len(profiles) == 2
    assert all(profile.countries == ("RU",) for profile in profiles)
    assert all(profile.description and profile.services for profile in profiles)
    assert all(profile.base_region == "RU-MOW" for profile in profiles)

    cleaning, office = profiles
    assert cleaning.delivery_mode is ServiceDeliveryMode.ONSITE
    assert office.delivery_mode is ServiceDeliveryMode.ONSITE
    assert cleaning.service_regions == office.service_regions == ("RU-MOW", "RU-MOS")
    assert cleaning.contractors_allowed is office.contractors_allowed is False
