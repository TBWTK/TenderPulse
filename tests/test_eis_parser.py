from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files
from io import BytesIO
from pathlib import Path
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.models import RecordKind, SourceCode
from tenderpulse.sources.common import SourceContractError, raw_sha256
from tenderpulse.sources.eis import parse_eis_legacy_xml, parse_eis_package

FIXTURES = Path(__file__).parent / "fixtures"
RUN_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_supported_eis_manual_xml_maps_traceable_notice() -> None:
    raw = (FIXTURES / "eis_legacy_notification.xml").read_bytes()

    records = parse_eis_legacy_xml(
        raw,
        ingestion_run_id=RUN_ID,
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
        source_url="manual://eis/eis_legacy_notification.xml",
    )

    assert len(records) == 1
    record = records[0]
    assert record.source is SourceCode.EIS
    assert record.kind is RecordKind.NOTICE
    assert record.source_record_id == "0123456789026000001"
    assert record.buyer_name == "ГБУЗ Демонстрационная больница"
    assert record.lots[0].amount is not None
    assert record.lots[0].currency == "RUB"
    assert record.evidence.source_url.startswith("https://zakupki.gov.ru/")


def test_mvp2_demo_export_maps_regions_classifications_deadlines_and_award() -> None:
    raw = files("tenderpulse.demo_data").joinpath("eis_legacy_notification.xml").read_bytes()

    records = parse_eis_legacy_xml(
        raw,
        ingestion_run_id=RUN_ID,
        observed_at=datetime(2026, 8, 15, tzinfo=UTC),
        source_url="manual://eis/demo/eis_legacy_notification.xml",
    )

    assert len(records) == 7
    assert sum(record.kind is RecordKind.NOTICE for record in records) == 6
    assert sum(record.kind is RecordKind.AWARD for record in records) == 1
    it_notice = next(record for record in records if record.source_record_id.endswith("003"))
    assert it_notice.region_codes == ("RU-PRI",)
    assert it_notice.delivery_location == "г. Владивосток, дистанционное выполнение работ"
    assert it_notice.delivery_mode is ServiceDeliveryMode.REMOTE
    assert it_notice.deadline_at == datetime.fromisoformat("2026-09-15T18:00:00+10:00")
    assert {(item.system, item.code) for item in it_notice.classifications} == {
        ("CPV", "72200000"),
        ("OKPD2", "62.01.11"),
    }
    assert "Работы допускаются удалённо" in it_notice.description
    award = next(record for record in records if record.kind is RecordKind.AWARD)
    assert award.supplier_names == ("ООО Надёжный автосервис",)
    assert award.lots[0].amount is not None
    assert award.lots[0].currency == "RUB"
    assert "contractCard" in award.evidence.source_url


def test_unknown_eis_schema_family_is_rejected() -> None:
    with pytest.raises(SourceContractError, match="schema family"):
        parse_eis_legacy_xml(
            b"<unknown><purchaseNumber>1</purchaseNumber></unknown>",
            ingestion_run_id=RUN_ID,
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            source_url="manual://eis/unknown.xml",
        )


def test_eis_dtd_is_rejected_before_parse() -> None:
    with pytest.raises(SourceContractError, match="DTD"):
        parse_eis_legacy_xml(
            b'<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]><export>&leak;</export>',
            ingestion_run_id=RUN_ID,
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            source_url="manual://eis/malicious.xml",
        )


def test_eis_zip_package_preserves_package_hash_and_member_locator() -> None:
    xml = (FIXTURES / "eis_legacy_notification.xml").read_bytes()
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("notifications/notice.xml", xml)
    raw = buffer.getvalue()

    records = parse_eis_package(
        raw,
        ingestion_run_id=RUN_ID,
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
        source_filename="eis_batch.zip",
    )

    assert len(records) == 1
    assert records[0].evidence.raw_sha256 == raw_sha256(raw)
    assert records[0].evidence.source_url.startswith("https://zakupki.gov.ru/")


def test_eis_zip_rejects_path_traversal() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../notice.xml", b"<xml/>")

    with pytest.raises(SourceContractError, match="unsafe member path"):
        parse_eis_package(
            buffer.getvalue(),
            ingestion_run_id=RUN_ID,
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            source_filename="unsafe.zip",
        )
