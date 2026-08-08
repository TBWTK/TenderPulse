from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from tenderpulse.domain.models import LifecycleStatus, RecordKind, SourceCode
from tenderpulse.sources.common import SourceContractError
from tenderpulse.sources.usaspending import parse_usaspending_response

FIXTURES = Path(__file__).parent / "fixtures"
RUN_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_usaspending_award_maps_winner_and_not_notice_deadline() -> None:
    raw = (FIXTURES / "usaspending_ai_awards.json").read_bytes()

    records = parse_usaspending_response(
        raw,
        ingestion_run_id=RUN_ID,
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
    )

    assert len(records) == 1
    record = records[0]
    assert record.source is SourceCode.USA_SPENDING
    assert record.kind is RecordKind.AWARD
    assert record.lifecycle is LifecycleStatus.AWARDED
    assert record.source_record_id == "W911QX20C0023"
    assert record.supplier_names == ("ECS FEDERAL, LLC",)
    assert record.buyer_name == "Department of Defense"
    assert record.lots[0].amount is not None
    assert record.lots[0].currency == "USD"
    assert record.deadline_at is None


def test_usaspending_missing_award_id_fails_loudly() -> None:
    with pytest.raises(SourceContractError, match="Award ID"):
        parse_usaspending_response(
            b'{"results":[{"Recipient Name":"Unknown"}]}',
            ingestion_run_id=RUN_ID,
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
        )
