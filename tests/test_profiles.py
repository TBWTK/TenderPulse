from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from tenderpulse.profiles import CompanyProfile


def _profile_payload() -> dict[str, object]:
    return {
        "slug": "company-profile",
        "version": 1,
        "name": "  Example   Company  ",
        "capabilities": ["  Cloud security  ", "cloud security", "Data platforms"],
        "positive_keywords": [" CLOUD ", "cloud", " data   mesh "],
        "classification_prefixes": {
            "cpv": ["72-00", "7200"],
            "okpd2": ["62.01"],
            "psc": ["d3"],
        },
        "countries": ["de", "DE", "us"],
        "min_amount": "100000",
        "max_amount": "5000000",
    }


def test_company_profile_normalizes_and_deduplicates_user_input() -> None:
    profile = CompanyProfile.model_validate(_profile_payload())

    assert profile.name == "Example Company"
    assert profile.capabilities == ("Cloud security", "Data platforms")
    assert profile.positive_keywords == ("cloud", "data mesh")
    assert profile.classification_prefixes == {
        "CPV": ("7200",),
        "OKPD2": ("62.01",),
        "PSC": ("D3",),
    }
    assert profile.countries == ("DE", "US")
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
