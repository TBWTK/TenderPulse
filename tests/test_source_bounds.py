from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from tenderpulse.sources.common import MAX_SOURCE_RECORDS, SourceContractError
from tenderpulse.sources.ted import TedQuery
from tenderpulse.sources.usaspending import USAspendingQuery


def test_ted_query_is_bounded_and_uses_official_v3_shape() -> None:
    query = TedQuery(
        published_from=date(2026, 8, 1),
        published_to=date(2026, 8, 8),
        cpv_prefixes=("72", "33"),
    )

    payload = query.to_payload()

    assert payload["limit"] == 100
    assert payload["paginationMode"] == "PAGE_NUMBER"
    assert payload["scope"] == "ACTIVE"
    assert "publication-date >= 20260801" in payload["query"]
    assert "classification-cpv" in payload["fields"]
    assert "deadline-receipt-tender-time-lot" in payload["fields"]


@pytest.mark.parametrize("limit", [0, MAX_SOURCE_RECORDS + 1])
def test_source_query_rejects_unbounded_limits(limit: int) -> None:
    with pytest.raises(ValidationError):
        TedQuery(
            published_from=date(2026, 8, 1),
            published_to=date(2026, 8, 8),
            limit=limit,
        )


def test_ted_query_rejects_large_date_window() -> None:
    with pytest.raises(ValidationError, match="90 days"):
        TedQuery(
            published_from=date(2026, 1, 1),
            published_to=date(2026, 8, 8),
        )


def test_usaspending_is_explicitly_outcome_only() -> None:
    query = USAspendingQuery(
        action_from=date(2025, 8, 8),
        action_to=date(2026, 8, 8),
        keywords=("artificial intelligence",),
    )

    assert query.supports_active_notices is False
    assert query.to_payload()["filters"]["award_type_codes"] == ["A", "B", "C", "D"]


def test_usaspending_rejects_empty_filters() -> None:
    with pytest.raises(SourceContractError, match="filter"):
        USAspendingQuery(
            action_from=date(2025, 8, 8),
            action_to=date(2026, 8, 8),
            keywords=(),
        ).to_payload()
