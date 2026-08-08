from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tenderpulse.domain.models import LifecycleStatus, RecordKind, SourceCode
from tenderpulse.sources.common import SourceContractError
from tenderpulse.sources.ted import parse_ted_response

FIXTURES = Path(__file__).parent / "fixtures"
RUN_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_ted_multilingual_record_normalizes_without_duplicate_codes() -> None:
    raw = (FIXTURES / "ted_search_medical.json").read_bytes()

    records = parse_ted_response(
        raw,
        ingestion_run_id=RUN_ID,
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
    )

    assert len(records) == 1
    record = records[0]
    assert record.source is SourceCode.TED
    assert record.kind is RecordKind.NOTICE
    assert record.lifecycle is LifecycleStatus.AWARDED
    assert record.source_record_id == "533445-2026"
    assert record.title.startswith("Italy")
    assert record.buyer_name == "ESTAR - Ente di Supporto Tecnico Amministrativo Regionale"
    assert [(code.system, code.code) for code in record.classifications] == [("CPV", "33190000")]
    assert record.countries == ("IT",)
    assert record.deadline_at is None
    assert record.evidence.raw_sha256
    assert record.evidence.source_url.endswith("533445-2026")


def test_ted_missing_natural_key_fails_loudly() -> None:
    payload = json.dumps({"notices": [{"notice-title": {"eng": "No ID"}}]}).encode()

    with pytest.raises(SourceContractError, match="publication-number"):
        parse_ted_response(
            payload,
            ingestion_run_id=RUN_ID,
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
        )


def test_ted_deadline_combines_source_date_time_and_offset() -> None:
    payload = json.dumps(
        {
            "notices": [
                {
                    "publication-number": "497954-2026",
                    "publication-date": "2026-07-20+02:00",
                    "notice-type": "cn-standard",
                    "notice-title": {"eng": "Electronic mail software package"},
                    "buyer-name": {"spa": ["Ayuntamiento de Sevilla"]},
                    "classification-cpv": ["48223000"],
                    "place-of-performance": ["ESP"],
                    "deadline-receipt-tender-date-lot": ["2026-08-17+02:00"],
                    "deadline-receipt-tender-time-lot": ["23:59:00+02:00"],
                }
            ]
        }
    ).encode()

    records = parse_ted_response(
        payload,
        ingestion_run_id=RUN_ID,
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
    )

    assert records[0].deadline_at is not None
    assert records[0].deadline_at.isoformat() == "2026-08-17T23:59:00+02:00"
