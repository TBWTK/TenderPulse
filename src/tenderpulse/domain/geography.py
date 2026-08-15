from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_RUSSIAN_REGION_RE = re.compile(r"^RU-[A-Z]{2,3}$")


class ServiceDeliveryMode(StrEnum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class GeographyStatus(StrEnum):
    SERVICE_REGION = "service_region"
    NATIONWIDE_REMOTE = "nationwide_remote"
    CONTRACTOR_COVERAGE = "contractor_coverage"
    TRAVEL_COVERAGE = "travel_coverage"
    EXCLUDED = "excluded"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GeographyAssessment:
    status: GeographyStatus
    region_codes: tuple[str, ...]


def normalize_russian_region(value: str) -> str:
    region = " ".join(value.split()).upper()
    if _RUSSIAN_REGION_RE.fullmatch(region) is None:
        raise ValueError("region must use an ISO 3166-2 Russian region code")
    return region


def assess_geography(
    *,
    profile_delivery_mode: ServiceDeliveryMode,
    service_regions: tuple[str, ...],
    nationwide: bool,
    travel_allowed: bool,
    contractors_allowed: bool,
    excluded_regions: tuple[str, ...],
    notice_delivery_mode: ServiceDeliveryMode,
    notice_regions: tuple[str, ...],
) -> GeographyAssessment:
    """Evaluate operational reach without inventing missing location facts."""
    if not notice_regions:
        return GeographyAssessment(GeographyStatus.UNKNOWN, ())

    regions = tuple(dict.fromkeys(notice_regions))
    if set(regions) & set(excluded_regions):
        return GeographyAssessment(GeographyStatus.EXCLUDED, regions)
    if set(regions) & set(service_regions):
        return GeographyAssessment(GeographyStatus.SERVICE_REGION, regions)

    remote_capable = profile_delivery_mode in {
        ServiceDeliveryMode.REMOTE,
        ServiceDeliveryMode.HYBRID,
    }
    onsite_required = notice_delivery_mode is ServiceDeliveryMode.ONSITE
    if nationwide and remote_capable and not onsite_required:
        return GeographyAssessment(GeographyStatus.NATIONWIDE_REMOTE, regions)
    if contractors_allowed:
        return GeographyAssessment(GeographyStatus.CONTRACTOR_COVERAGE, regions)
    if travel_allowed:
        return GeographyAssessment(GeographyStatus.TRAVEL_COVERAGE, regions)
    return GeographyAssessment(GeographyStatus.OUT_OF_SCOPE, regions)


__all__ = [
    "GeographyAssessment",
    "GeographyStatus",
    "ServiceDeliveryMode",
    "assess_geography",
    "normalize_russian_region",
]
