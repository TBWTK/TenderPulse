from __future__ import annotations

import json
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CLASSIFICATION_SYSTEMS = frozenset({"CPV", "OKPD2", "PSC"})
_CLASSIFICATION_PREFIX_RE = re.compile(r"^[A-Z0-9.]+$")
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


class CompanyProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    version: int = Field(ge=1)
    name: str = Field(min_length=1)
    capabilities: tuple[str, ...]
    positive_keywords: tuple[str, ...]
    classification_prefixes: dict[str, tuple[str, ...]]
    countries: tuple[str, ...]
    min_amount: Decimal | None = Field(default=None, ge=0)
    max_amount: Decimal | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _collapse_whitespace(value)
        if not normalized:
            raise ValueError("name cannot be empty")
        return normalized

    @field_validator("capabilities")
    @classmethod
    def normalize_capabilities(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_text_values(values, field_name="capabilities", casefold=False)

    @field_validator("positive_keywords")
    @classmethod
    def normalize_keywords(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_text_values(values, field_name="positive_keywords", casefold=True)

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

    @model_validator(mode="after")
    def validate_amount_range(self) -> Self:
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("min_amount cannot exceed max_amount")
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


@lru_cache(maxsize=1)
def load_demo_profiles() -> tuple[CompanyProfile, ...]:
    path = Path(__file__).with_name("demo_profiles.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = tuple(CompanyProfile.model_validate(item) for item in payload)
    if len(profiles) != 2:
        raise RuntimeError("demo profile authority must contain exactly two profiles")
    return profiles
