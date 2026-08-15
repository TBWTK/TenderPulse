from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.models import (
    ClassificationCode,
    LifecycleStatus,
    Lot,
    ProcurementRecord,
    RecordKind,
    SourceCode,
    SourceEvidence,
)

RUN_ID = UUID("00000000-0000-0000-0000-000000000001")


def build_record(
    *,
    source: SourceCode = SourceCode.TED,
    source_record_id: str = "record-1",
    title: str = "Cloud data platform implementation",
    description: str = "Data engineering, analytics and machine learning platform services",
    codes: tuple[ClassificationCode, ...] = (ClassificationCode(system="CPV", code="72200000"),),
    countries: tuple[str, ...] = ("DE",),
    region_codes: tuple[str, ...] = (),
    delivery_location: str | None = None,
    delivery_mode: ServiceDeliveryMode = ServiceDeliveryMode.UNKNOWN,
    amount: Decimal | None = Decimal("500000"),
    currency: str | None = "EUR",
    deadline_at: datetime | None = datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
    raw_sha256: str = "a" * 64,
) -> ProcurementRecord:
    return ProcurementRecord(
        source=source,
        source_record_id=source_record_id,
        kind=RecordKind.NOTICE,
        lifecycle=LifecycleStatus.ACTIVE,
        title=title,
        description=description,
        buyer_name="Public Buyer",
        supplier_names=(),
        classifications=codes,
        countries=countries,
        region_codes=region_codes,
        delivery_location=delivery_location,
        delivery_mode=delivery_mode,
        published_at=datetime(2026, 8, 3, tzinfo=UTC),
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
        deadline_at=deadline_at,
        lots=(
            Lot(
                source_lot_id="LOT-1",
                title=title,
                amount=amount,
                currency=currency,
                deadline_at=deadline_at,
                classifications=codes,
            ),
        ),
        evidence=SourceEvidence(
            raw_sha256=raw_sha256,
            ingestion_run_id=RUN_ID,
            source_url=f"https://example.test/{source_record_id}",
        ),
    )


@pytest.fixture
def it_notice() -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        countries=("RU",),
        region_codes=("RU-PRI",),
        delivery_location="Владивосток",
        delivery_mode=ServiceDeliveryMode.REMOTE,
        currency="RUB",
    )


@pytest.fixture
def medical_notice() -> ProcurementRecord:
    return build_record(
        source_record_id="533445-2026",
        title="Supply of orthopaedic medical devices and laboratory consumables",
        description="Medical devices, diagnostic reagents and laboratory supplies in 20 lots",
        codes=(ClassificationCode(system="CPV", code="33190000"),),
        countries=("IT",),
        amount=None,
        currency=None,
        deadline_at=None,
        raw_sha256="b" * 64,
    )


@pytest.fixture
def unrelated_notice() -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id="construction-1",
        title="Winter road construction and maintenance",
        description="Road works and snow removal services",
        codes=(ClassificationCode(system="CPV", code="45000000"),),
        countries=("RU",),
        region_codes=("RU-MOW",),
        delivery_location="Москва",
        delivery_mode=ServiceDeliveryMode.ONSITE,
        currency="RUB",
        raw_sha256="c" * 64,
    )


@pytest.fixture
def auto_notice() -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id="auto-moscow",
        title="Техническое обслуживание и ремонт автомобилей",
        description="Ремонт и мойка служебного автотранспорта заказчика",
        codes=(ClassificationCode(system="CPV", code="50110000"),),
        countries=("RU",),
        region_codes=("RU-MOW",),
        delivery_location="Москва",
        delivery_mode=ServiceDeliveryMode.ONSITE,
        currency="RUB",
        raw_sha256="d" * 64,
    )


@pytest.fixture
def landscaping_notice() -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id="landscaping-moscow",
        title="Озеленение и благоустройство городской территории",
        description="Устройство газонов, клумб и посадка кустарников",
        codes=(ClassificationCode(system="CPV", code="45112710"),),
        countries=("RU",),
        region_codes=("RU-MOW",),
        delivery_location="Москва",
        delivery_mode=ServiceDeliveryMode.ONSITE,
        currency="RUB",
        raw_sha256="e" * 64,
    )


@pytest.fixture
def cleaning_notice() -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id="cleaning-moscow",
        title="Комплексная уборка помещений и дворов",
        description="Ежедневный клининг и санитарное содержание территории",
        codes=(ClassificationCode(system="CPV", code="90910000"),),
        countries=("RU",),
        region_codes=("RU-MOW",),
        delivery_location="Москва",
        delivery_mode=ServiceDeliveryMode.ONSITE,
        currency="RUB",
        raw_sha256="f" * 64,
    )


@pytest.fixture
def office_notice() -> ProcurementRecord:
    return build_record(
        source=SourceCode.EIS,
        source_record_id="office-supply-moscow",
        title="Поставка офисной мебели, канцелярии и МФУ",
        description="Столы, шкафы, бумага, принтеры и картриджи для административного здания",
        codes=(
            ClassificationCode(system="CPV", code="39130000"),
            ClassificationCode(system="OKPD2", code="31.01.12"),
        ),
        countries=("RU",),
        region_codes=("RU-MOW",),
        delivery_location="Москва",
        delivery_mode=ServiceDeliveryMode.ONSITE,
        currency="RUB",
        raw_sha256="1" * 64,
    )
