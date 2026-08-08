from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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

    @field_validator("classification_prefixes")
    @classmethod
    def normalize_prefixes(
        cls,
        value: dict[str, tuple[str, ...]],
    ) -> dict[str, tuple[str, ...]]:
        return {
            system.upper(): tuple(
                prefix.replace("-", "").replace(" ", "").upper() for prefix in prefixes
            )
            for system, prefixes in value.items()
        }

    @field_validator("countries")
    @classmethod
    def normalize_countries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(country.upper() for country in value)

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


@lru_cache(maxsize=1)
def load_demo_profiles() -> tuple[CompanyProfile, ...]:
    path = Path(__file__).with_name("demo_profiles.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = tuple(CompanyProfile.model_validate(item) for item in payload)
    if len(profiles) != 2:
        raise RuntimeError("demo profile authority must contain exactly two profiles")
    return profiles
