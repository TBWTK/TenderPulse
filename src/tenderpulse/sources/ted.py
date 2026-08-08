from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tenderpulse.domain.models import (
    ClassificationCode,
    LifecycleStatus,
    Lot,
    ProcurementRecord,
    RecordKind,
    SourceCode,
    SourceEvidence,
)
from tenderpulse.sources.common import (
    DEFAULT_SOURCE_RECORDS,
    MAX_SOURCE_RECORDS,
    SourceContractError,
    raw_sha256,
)

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
_TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "notice-type",
    "classification-cpv",
    "description-proc",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
    "place-of-performance",
    "links",
]
_ISO3_TO_2 = {
    "AUT": "AT",
    "BEL": "BE",
    "BGR": "BG",
    "CZE": "CZ",
    "DEU": "DE",
    "DNK": "DK",
    "ESP": "ES",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "GRC": "GR",
    "HRV": "HR",
    "HUN": "HU",
    "IRL": "IE",
    "ITA": "IT",
    "LTU": "LT",
    "LUX": "LU",
    "LVA": "LV",
    "MLT": "MT",
    "NLD": "NL",
    "POL": "PL",
    "PRT": "PT",
    "ROU": "RO",
    "SVK": "SK",
    "SVN": "SI",
    "SWE": "SE",
}


class TedQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    published_from: date
    published_to: date
    cpv_prefixes: tuple[str, ...] = ()
    limit: int = Field(default=DEFAULT_SOURCE_RECORDS, ge=1, le=MAX_SOURCE_RECORDS)
    page: int = Field(default=1, ge=1)

    @field_validator("cpv_prefixes")
    @classmethod
    def validate_cpv_prefixes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(prefix.strip() for prefix in value)
        if any(not prefix.isdigit() or len(prefix) > 8 for prefix in cleaned):
            raise ValueError("CPV prefixes must contain one to eight digits")
        return cleaned

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.published_to < self.published_from:
            raise ValueError("published_to cannot precede published_from")
        if (self.published_to - self.published_from).days > 90:
            raise ValueError("TED date window cannot exceed 90 days")
        return self

    def to_payload(self) -> dict[str, Any]:
        clauses = [
            f"publication-date >= {self.published_from:%Y%m%d}",
            f"publication-date <= {self.published_to:%Y%m%d}",
        ]
        if self.cpv_prefixes:
            hierarchical_codes = " ".join(prefix.ljust(8, "0") for prefix in self.cpv_prefixes)
            clauses.append(f"classification-cpv IN ({hierarchical_codes})")
        return {
            "query": " AND ".join(clauses),
            "fields": list(_TED_FIELDS),
            "limit": self.limit,
            "page": self.page,
            "scope": "ACTIVE",
            "checkQuerySyntax": False,
            "paginationMode": "PAGE_NUMBER",
        }


def parse_ted_response(
    raw: bytes,
    *,
    ingestion_run_id: UUID,
    observed_at: datetime,
) -> tuple[ProcurementRecord, ...]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceContractError("TED response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("notices"), list):
        raise SourceContractError("TED response must contain a notices array")

    digest = raw_sha256(raw)
    records: list[ProcurementRecord] = []
    for item in payload["notices"]:
        if not isinstance(item, dict):
            raise SourceContractError("TED notice must be an object")
        source_id = item.get("publication-number")
        if not isinstance(source_id, str) or not source_id:
            raise SourceContractError("TED notice is missing publication-number")

        title = _localized_text(item.get("notice-title"))
        if not title:
            raise SourceContractError(f"TED notice {source_id} is missing notice-title")
        description = _localized_text(item.get("description-proc")) or ""
        buyer_name = _localized_text(item.get("buyer-name")) or None
        cpv_values = item.get("classification-cpv") or []
        if not isinstance(cpv_values, list):
            raise SourceContractError(f"TED notice {source_id} classification-cpv must be an array")
        classifications = tuple(
            ClassificationCode(system="CPV", code=code)
            for code in dict.fromkeys(str(code) for code in cpv_values)
        )
        place_values = item.get("place-of-performance") or []
        countries = tuple(
            dict.fromkeys(
                mapped
                for value in place_values
                if isinstance(value, str)
                for mapped in [_ISO3_TO_2.get(value.upper())]
                if mapped is not None
            )
        )
        source_url = _ted_source_url(item, source_id)
        lifecycle = _ted_lifecycle(item.get("notice-type"))
        deadline = _parse_ted_deadline(
            item.get("deadline-receipt-tender-date-lot"),
            item.get("deadline-receipt-tender-time-lot"),
        )
        published_at = _parse_ted_publication_date(item.get("publication-date"))
        lot = Lot(
            source_lot_id="NOTICE",
            title=title,
            amount=None,
            currency=None,
            deadline_at=deadline,
            classifications=classifications,
        )
        records.append(
            ProcurementRecord(
                source=SourceCode.TED,
                source_record_id=source_id,
                kind=RecordKind.NOTICE,
                lifecycle=lifecycle,
                title=title,
                description=description,
                buyer_name=buyer_name,
                supplier_names=(),
                classifications=classifications,
                countries=countries,
                published_at=published_at,
                observed_at=observed_at,
                deadline_at=deadline,
                lots=(lot,),
                evidence=SourceEvidence(
                    raw_sha256=digest,
                    ingestion_run_id=ingestion_run_id,
                    source_url=source_url,
                ),
            )
        )
    return tuple(records)


def _localized_text(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return None
    keys = sorted(value, key=lambda key: (key not in {"eng", "rus", "en", "ru"}, key))
    for key in keys:
        candidate = value[key]
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return None


def _ted_source_url(item: dict[str, Any], source_id: str) -> str:
    links = item.get("links")
    if isinstance(links, dict):
        html = links.get("html")
        if isinstance(html, dict):
            for language in ("ENG", "RUS"):
                candidate = html.get(language)
                if isinstance(candidate, str) and candidate.startswith("https://ted.europa.eu/"):
                    return candidate
            for candidate in html.values():
                if isinstance(candidate, str) and candidate.startswith("https://ted.europa.eu/"):
                    return candidate
    return f"https://ted.europa.eu/en/notice/-/detail/{source_id}"


def _ted_lifecycle(value: object) -> LifecycleStatus:
    notice_type = str(value or "").lower()
    if notice_type.startswith("can"):
        return LifecycleStatus.AWARDED
    if notice_type.startswith("pin"):
        return LifecycleStatus.PLANNED
    if notice_type.startswith(("cn", "qu", "subco")):
        return LifecycleStatus.ACTIVE
    return LifecycleStatus.UNKNOWN


def _parse_ted_deadline(date_value: object, time_value: object) -> datetime | None:
    dates = date_value if isinstance(date_value, list) else [date_value]
    times = time_value if isinstance(time_value, list) else [time_value]
    parsed: list[datetime] = []
    for source_date, source_time in zip(dates, times, strict=False):
        if not isinstance(source_date, str) or not isinstance(source_time, str):
            continue
        if len(source_date) < 10 or len(source_time) < 8:
            continue
        offset = source_time[8:] or source_date[10:]
        candidate = f"{source_date[:10]}T{source_time[:8]}{offset}"
        try:
            result = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            continue
        if result.tzinfo is not None and result.utcoffset() is not None:
            parsed.append(result)
    return min(parsed) if parsed else None


def _parse_ted_publication_date(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        source_date = date.fromisoformat(value[:10])
    except ValueError:
        return None
    offset = value[10:]
    tz = UTC
    if len(offset) == 6 and offset[0] in "+-" and offset[1:3].isdigit() and offset[4:].isdigit():
        delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[4:]))
        tz = timezone(delta if offset[0] == "+" else -delta)
    return datetime.combine(source_date, time.min, tzinfo=tz)
