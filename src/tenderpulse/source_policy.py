from __future__ import annotations

from collections.abc import Iterable

from tenderpulse.domain.models import ProcurementRecord, SourceCode

CURRENT_PRODUCT_SOURCES: tuple[SourceCode, ...] = (SourceCode.EIS,)


def is_current_product_record(record: ProcurementRecord) -> bool:
    return record.source in CURRENT_PRODUCT_SOURCES and "RU" in record.countries


def current_product_records(
    records: Iterable[ProcurementRecord],
) -> tuple[ProcurementRecord, ...]:
    return tuple(record for record in records if is_current_product_record(record))


__all__ = [
    "CURRENT_PRODUCT_SOURCES",
    "current_product_records",
    "is_current_product_record",
]
