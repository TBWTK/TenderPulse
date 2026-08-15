from __future__ import annotations

import json
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tenderpulse.domain.geography import ServiceDeliveryMode, normalize_russian_region

_CLASSIFICATION_SYSTEMS = frozenset({"CPV", "OKPD2", "PSC"})
_CLASSIFICATION_PREFIX_RE = re.compile(r"^[A-Z0-9.]+$")
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


class CompanyProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1)
    description: str = ""
    services: tuple[str, ...] = ()
    capabilities: tuple[str, ...]
    positive_keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...] = ()
    classification_prefixes: dict[str, tuple[str, ...]]
    countries: tuple[str, ...]
    customer_types: tuple[str, ...] = ()
    base_region: str | None = None
    service_regions: tuple[str, ...] = ()
    delivery_mode: ServiceDeliveryMode = ServiceDeliveryMode.UNKNOWN
    nationwide: bool = False
    travel_allowed: bool = False
    contractors_allowed: bool = False
    excluded_regions: tuple[str, ...] = ()
    participation_constraints: tuple[str, ...] = ()
    min_amount: Decimal | None = Field(default=None, ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _collapse_whitespace(value)
        if not normalized:
            raise ValueError("name cannot be empty")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return _collapse_whitespace(value)

    @field_validator("services")
    @classmethod
    def normalize_services(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_optional_text_values(values, casefold=False)

    @field_validator("capabilities")
    @classmethod
    def normalize_capabilities(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_text_values(values, field_name="capabilities", casefold=False)

    @field_validator("positive_keywords")
    @classmethod
    def normalize_keywords(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_text_values(values, field_name="positive_keywords", casefold=True)

    @field_validator("negative_keywords")
    @classmethod
    def normalize_negative_keywords(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_optional_text_values(values, casefold=True)

    @field_validator("classification_prefixes")
    @classmethod
    def normalize_prefixes(
        cls,
        value: dict[str, tuple[str, ...]],
    ) -> dict[str, tuple[str, ...]]:
        normalized: dict[str, list[str]] = {}
        for raw_system, prefixes in value.items():
            system = _collapse_whitespace(raw_system).upper()
            if system not in _CLASSIFICATION_SYSTEMS:
                raise ValueError(f"unsupported classification system: {raw_system}")
            if not prefixes:
                raise ValueError(f"classification prefix is required for {system}")
            system_prefixes = normalized.setdefault(system, [])
            for raw_prefix in prefixes:
                prefix = re.sub(r"[-\s]", "", raw_prefix).upper()
                if not prefix or _CLASSIFICATION_PREFIX_RE.fullmatch(prefix) is None:
                    raise ValueError(f"invalid classification prefix for {system}")
                if prefix not in system_prefixes:
                    system_prefixes.append(prefix)
        if not normalized:
            raise ValueError("at least one classification prefix is required")
        return {system: tuple(prefixes) for system, prefixes in normalized.items()}

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw_country in value:
            country = _collapse_whitespace(raw_country).upper()
            if _COUNTRY_RE.fullmatch(country) is None:
                raise ValueError("countries must use ISO 3166-1 alpha-2 codes")
            if country not in normalized:
                normalized.append(country)
        if not normalized:
            raise ValueError("at least one ISO 3166-1 alpha-2 country is required")
        return tuple(normalized)

    @field_validator("customer_types", "participation_constraints")
    @classmethod
    def normalize_optional_profile_text(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_optional_text_values(values, casefold=False)

    @field_validator("base_region")
    @classmethod
    def normalize_base_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_russian_region(value)

    @field_validator("service_regions", "excluded_regions")
    @classmethod
    def normalize_region_list(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(normalize_russian_region(value) for value in values))

    @model_validator(mode="after")
    def validate_amount_range(self) -> Self:
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("min_amount cannot exceed max_amount")
        overlap = set(self.service_regions) & set(self.excluded_regions)
        if overlap:
            raise ValueError("service_regions and excluded_regions cannot overlap")
        if self.base_region is not None and self.base_region in self.excluded_regions:
            raise ValueError("base_region cannot be excluded")
        return self

    def accepts_amount(self, amount: Decimal) -> bool:
        if self.min_amount is not None and amount < self.min_amount:
            return False
        return self.max_amount is None or amount <= self.max_amount


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalize_text_values(
    values: tuple[str, ...],
    *,
    field_name: str,
    casefold: bool,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = _collapse_whitespace(raw_value)
        if not value:
            raise ValueError(f"{field_name} cannot contain empty values")
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key if casefold else value)
    if not normalized:
        raise ValueError(f"{field_name} must contain at least one value")
    return tuple(normalized)


def _normalize_optional_text_values(
    values: tuple[str, ...],
    *,
    casefold: bool,
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = _collapse_whitespace(raw_value)
        if not value:
            raise ValueError("optional text values cannot contain empty values")
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key if casefold else value)
    return tuple(normalized)


@lru_cache(maxsize=1)
def load_demo_profiles() -> tuple[CompanyProfile, ...]:
    path = Path(__file__).with_name("demo_profiles.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = tuple(CompanyProfile.model_validate(item) for item in payload)
    if len(profiles) != 4 or len({profile.slug for profile in profiles}) != 4:
        raise RuntimeError("demo profile authority must contain four distinct profiles")
    return profiles
