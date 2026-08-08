from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

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
    assert record.evidence.source_url.startswith("manual://")


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
    assert records[0].evidence.source_url == (
        "manual://eis/upload/eis_batch.zip/notifications/notice.xml"
    )


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
