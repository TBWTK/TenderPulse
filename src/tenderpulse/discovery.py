from __future__ import annotations

from dataclasses import dataclass

from tenderpulse.profiles import CompanyProfile
from tenderpulse.sources.eis_rss import normalize_eis_search_string

DISCOVERY_STRATEGY_VERSION = "eis-profile-services-v1"
MAX_QUERIES_PER_PROFILE = 3
MAX_DISCOVERY_QUERIES = 30


@dataclass(frozen=True, slots=True)
class EisDiscoveryPlanItem:
    profile_slug: str
    profile_version: int
    search_string: str
    strategy_version: str = DISCOVERY_STRATEGY_VERSION


def build_eis_discovery_plan(
    profiles: tuple[CompanyProfile, ...],
) -> tuple[EisDiscoveryPlanItem, ...]:
    if not profiles or len({profile.slug for profile in profiles}) != len(profiles):
        raise RuntimeError("discovery requires distinct active company profiles")

    plan: list[EisDiscoveryPlanItem] = []
    for profile in profiles:
        candidates = profile.services or profile.positive_keywords
        selected: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            phrase = normalize_eis_search_string(candidate)
            assert phrase is not None
            key = phrase.casefold()
            if key in seen:
                continue
            seen.add(key)
            selected.append(phrase)
            if len(selected) == MAX_QUERIES_PER_PROFILE:
                break
        if not selected:
            raise RuntimeError(f"profile {profile.slug} has no EIS discovery phrase")
        plan.extend(
            EisDiscoveryPlanItem(
                profile_slug=profile.slug,
                profile_version=profile.version,
                search_string=phrase,
            )
            for phrase in selected
        )

    if len(plan) > MAX_DISCOVERY_QUERIES:
        raise RuntimeError(f"discovery query limit exceeded: {len(plan)} > {MAX_DISCOVERY_QUERIES}")
    return tuple(plan)
