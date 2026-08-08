from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar, Self
from urllib.parse import quote
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tenderpulse.domain.models import (
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

USA_SPENDING_SEARCH_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


class USAspendingQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    supports_active_notices: ClassVar[bool] = False
    action_from: date
    action_to: date
    keywords: tuple[str, ...] = ()
    limit: int = Field(default=DEFAULT_SOURCE_RECORDS, ge=1, le=MAX_SOURCE_RECORDS)
    page: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.action_to < self.action_from:
            raise ValueError("action_to cannot precede action_from")
        if (self.action_to - self.action_from).days > 731:
            raise ValueError("USAspending MVP window cannot exceed 24 months")
        return self

    def to_payload(self) -> dict[str, Any]:
        keywords = [keyword.strip() for keyword in self.keywords if keyword.strip()]
        if not keywords:
            raise SourceContractError("USAspending query requires at least one business filter")
        return {
            "filters": {
                "keywords": keywords,
                "time_period": [
                    {
                        "start_date": self.action_from.isoformat(),
                        "end_date": self.action_to.isoformat(),
                    }
                ],
                "award_type_codes": ["A", "B", "C", "D"],
            },
            "fields": [
                "Award ID",
                "Recipient Name",
                "Award Amount",
                "Description",
                "Start Date",
                "End Date",
                "Awarding Agency",
                "Awarding Sub Agency",
            ],
            "page": self.page,
            "limit": self.limit,
            "sort": "Award Amount",
            "order": "desc",
            "subawards": False,
        }


def parse_usaspending_response(
    raw: bytes,
    *,
    ingestion_run_id: UUID,
    observed_at: datetime,
) -> tuple[ProcurementRecord, ...]:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceContractError("USAspending response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise SourceContractError("USAspending response must contain a results array")

    digest = raw_sha256(raw)
    records: list[ProcurementRecord] = []
    for item in payload["results"]:
        if not isinstance(item, dict):
            raise SourceContractError("USAspending award must be an object")
        award_id = item.get("Award ID")
        if not isinstance(award_id, str) or not award_id:
            raise SourceContractError("USAspending result is missing Award ID")
        recipient = _optional_text(item.get("Recipient Name"))
        agency = _optional_text(item.get("Awarding Agency"))
        description = _optional_text(item.get("Description")) or ""
        amount = _decimal_or_error(item.get("Award Amount"), award_id)
        generated_id = _optional_text(item.get("generated_internal_id")) or award_id
        source_url = f"https://www.usaspending.gov/award/{quote(generated_id, safe='-_')}"
        lot = Lot(
            source_lot_id="AWARD",
            title=description or f"US federal award {award_id}",
            amount=amount,
            currency="USD" if amount is not None else None,
            deadline_at=None,
            classifications=(),
        )
        records.append(
            ProcurementRecord(
                source=SourceCode.USA_SPENDING,
                source_record_id=award_id,
                kind=RecordKind.AWARD,
                lifecycle=LifecycleStatus.AWARDED,
                title=description or f"US federal award {award_id}",
                description=description,
                buyer_name=agency,
                supplier_names=(recipient,) if recipient else (),
                classifications=(),
                countries=(),
                published_at=None,
                observed_at=observed_at,
                deadline_at=None,
                lots=(lot,),
                evidence=SourceEvidence(
                    raw_sha256=digest,
                    ingestion_run_id=ingestion_run_id,
                    source_url=source_url,
                ),
            )
        )
    return tuple(records)


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _decimal_or_error(value: object, award_id: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise SourceContractError(f"USAspending award {award_id} has invalid Award Amount") from exc
