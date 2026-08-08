from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from tenderpulse.domain.models import ProcurementRecord, RecordKind, SourceCode


class CoverageStatus(StrEnum):
    FOUND = "found"
    UNKNOWN = "unknown"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"


class AwardOutcomeView(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_source: SourceCode
    record_source_id: str
    title: str
    buyer_name: str | None
    supplier_names: tuple[str, ...]
    winner_status: CoverageStatus
    amount: Decimal | None
    currency: str | None
    amount_status: CoverageStatus
    observed_at: datetime
    raw_sha256: str
    source_url: str


def build_award_outcome(record: ProcurementRecord) -> AwardOutcomeView:
    if record.kind is not RecordKind.AWARD:
        raise ValueError("award outcome requires an award record")
    known_amounts = tuple(
        (lot.amount, lot.currency) for lot in record.lots if lot.amount is not None
    )
    if not known_amounts:
        amount = None
        currency = None
        amount_status = CoverageStatus.UNKNOWN
    elif len(known_amounts) != len(record.lots):
        amount = None
        currency = None
        amount_status = CoverageStatus.PARTIAL
    elif len({currency for _, currency in known_amounts}) != 1:
        amount = None
        currency = None
        amount_status = CoverageStatus.CONFLICTING
    else:
        amount = sum((value for value, _ in known_amounts), start=Decimal(0))
        currency = known_amounts[0][1]
        amount_status = CoverageStatus.FOUND
    return AwardOutcomeView(
        record_source=record.source,
        record_source_id=record.source_record_id,
        title=record.title,
        buyer_name=record.buyer_name,
        supplier_names=record.supplier_names,
        winner_status=(CoverageStatus.FOUND if record.supplier_names else CoverageStatus.UNKNOWN),
        amount=amount,
        currency=currency,
        amount_status=amount_status,
        observed_at=record.observed_at,
        raw_sha256=record.evidence.raw_sha256,
        source_url=record.evidence.source_url,
    )
