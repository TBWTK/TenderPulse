from __future__ import annotations

from decimal import Decimal

import pytest

from tenderpulse.domain.models import Lot, ProcurementRecord, RecordKind
from tenderpulse.outcomes import CoverageStatus, build_award_outcome


def test_partial_and_conflicting_lot_amounts_never_look_like_a_total(
    it_notice: ProcurementRecord,
) -> None:
    base = it_notice.model_copy(update={"kind": RecordKind.AWARD})
    priced = base.lots[0].model_copy(update={"amount": Decimal("10"), "currency": "USD"})
    missing = Lot(source_lot_id="missing", title="Amount not published")
    eur = base.lots[0].model_copy(
        update={"source_lot_id": "eur", "amount": Decimal("9"), "currency": "EUR"}
    )

    partial = build_award_outcome(base.model_copy(update={"lots": (priced, missing)}))
    conflicting = build_award_outcome(base.model_copy(update={"lots": (priced, eur)}))

    assert (partial.amount_status, partial.amount, partial.currency) == (
        CoverageStatus.PARTIAL,
        None,
        None,
    )
    assert (conflicting.amount_status, conflicting.amount, conflicting.currency) == (
        CoverageStatus.CONFLICTING,
        None,
        None,
    )


def test_non_award_cannot_be_projected_as_outcome(it_notice: ProcurementRecord) -> None:
    with pytest.raises(ValueError, match="award record"):
        build_award_outcome(it_notice)
