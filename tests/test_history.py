from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tenderpulse.domain.history import ChangeKind, VersionHistory
from tenderpulse.domain.models import ProcurementRecord


def test_identical_replay_is_idempotent(it_notice: ProcurementRecord) -> None:
    history = VersionHistory()
    first = history.apply(it_notice, at=datetime(2026, 8, 8, tzinfo=UTC))
    replay = history.apply(
        it_notice.model_copy(update={"observed_at": datetime(2026, 8, 9, tzinfo=UTC)}),
        at=datetime(2026, 8, 9, tzinfo=UTC),
    )

    assert first.kind is ChangeKind.CREATED
    assert replay.kind is ChangeKind.UNCHANGED
    assert len(history.versions_for(it_notice.natural_key)) == 1


def test_changed_canonical_payload_creates_scd2_version(it_notice: ProcurementRecord) -> None:
    history = VersionHistory()
    started = datetime(2026, 8, 8, tzinfo=UTC)
    changed_at = started + timedelta(days=1)
    history.apply(it_notice, at=started)

    result = history.apply(
        it_notice.model_copy(update={"title": "Cloud platform implementation — corrected"}),
        at=changed_at,
    )
    versions = history.versions_for(it_notice.natural_key)

    assert result.kind is ChangeKind.UPDATED
    assert [version.version for version in versions] == [1, 2]
    assert versions[0].valid_from == started
    assert versions[0].valid_to == changed_at
    assert versions[1].valid_from == changed_at
    assert versions[1].valid_to is None
    assert versions[0].record.title != versions[1].record.title


def test_time_must_move_forward(it_notice: ProcurementRecord) -> None:
    history = VersionHistory()
    at = datetime(2026, 8, 8, tzinfo=UTC)
    history.apply(it_notice, at=at)

    try:
        history.apply(it_notice.model_copy(update={"title": "changed"}), at=at)
    except ValueError as exc:
        assert "strictly after" in str(exc)
    else:
        raise AssertionError("non-monotonic SCD2 time must fail loudly")
