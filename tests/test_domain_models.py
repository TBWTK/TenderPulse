from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tenderpulse.domain.models import ClassificationCode, Lot, SourceEvidence


def test_unknown_amount_and_deadline_remain_none() -> None:
    lot = Lot(
        source_lot_id="LOT-1",
        title="Unpriced lot",
        amount=None,
        currency=None,
        deadline_at=None,
        classifications=(),
    )

    assert lot.amount is None
    assert lot.currency is None
    assert lot.deadline_at is None


@pytest.mark.parametrize(
    ("amount", "currency"),
    [(Decimal("1"), None), (None, "EUR")],
)
def test_amount_and_currency_must_be_known_together(
    amount: Decimal | None,
    currency: str | None,
) -> None:
    with pytest.raises(ValidationError, match="amount and currency"):
        Lot(
            source_lot_id="LOT-1",
            title="Broken money",
            amount=amount,
            currency=currency,
            deadline_at=None,
            classifications=(),
        )


def test_classification_normalizes_system_and_code() -> None:
    code = ClassificationCode(system="cpv", code=" 7220-0000 ")

    assert code.system == "CPV"
    assert code.code == "72200000"


def test_source_evidence_rejects_non_sha256() -> None:
    with pytest.raises(ValidationError, match="SHA-256"):
        SourceEvidence(
            raw_sha256="not-a-hash",
            ingestion_run_id="00000000-0000-0000-0000-000000000001",
            source_url="https://example.test/source",
        )


def test_deadline_requires_timezone() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        Lot(
            source_lot_id="LOT-1",
            title="Naive deadline",
            amount=None,
            currency=None,
            deadline_at=datetime(2026, 9, 1),
            classifications=(),
        )


def test_aware_deadline_is_accepted() -> None:
    deadline = datetime(2026, 9, 1, tzinfo=UTC)
    lot = Lot(
        source_lot_id="LOT-1",
        title="Aware deadline",
        amount=None,
        currency=None,
        deadline_at=deadline,
        classifications=(),
    )

    assert lot.deadline_at == deadline
