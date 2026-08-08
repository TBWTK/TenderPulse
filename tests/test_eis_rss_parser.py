from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from tenderpulse.domain.models import LifecycleStatus, SourceCode
from tenderpulse.sources.common import SourceContractError
from tenderpulse.sources.eis_rss import EisRssQuery, parse_eis_rss

FIXTURES = Path(__file__).parent / "fixtures"


def test_official_eis_rss_maps_bounded_traceable_notices() -> None:
    raw = (FIXTURES / "eis_search_rss.xml").read_bytes()
    records = parse_eis_rss(
        raw,
        observed_at=datetime(2026, 8, 8, 2, tzinfo=UTC),
        ingestion_run_id=UUID("00000000-0000-0000-0000-000000000001"),
        limit=10,
    )

    assert len(records) == 2
    active = records[0]
    assert active.source is SourceCode.EIS
    assert active.source_record_id == "0345300035126000286"
    assert active.lifecycle is LifecycleStatus.ACTIVE
    assert active.title == "Поставка медицинских изделий"
    assert active.buyer_name == "ГБУЗ ДЕМО БОЛЬНИЦА"
    assert active.countries == ("RU",)
    assert active.published_at == datetime(2026, 8, 7, 20, 11, 2, tzinfo=UTC)
    assert active.deadline_at is None
    assert active.lots[0].amount == Decimal("96882.20")
    assert active.lots[0].currency == "RUB"
    assert active.evidence.source_url.endswith("regNumber=0345300035126000286")
    assert active.evidence.raw_sha256 == hashlib.sha256(raw).hexdigest()

    cancelled = records[1]
    assert cancelled.lifecycle is LifecycleStatus.CANCELLED
    assert cancelled.title == "Электронный аукцион №0123456789012345678"
    assert cancelled.lots[0].amount is None
    assert cancelled.lots[0].currency is None


def test_eis_rss_query_is_date_and_count_bounded() -> None:
    query = EisRssQuery(
        published_from=date(2026, 8, 1),
        published_to=date(2026, 8, 8),
        limit=17,
    )

    assert query.to_params() == {
        "fz44": "on",
        "pageNumber": "1",
        "recordsPerPage": "_20",
        "sortBy": "UPDATE_DATE",
        "sortDirection": "false",
        "publishDateFrom": "01.08.2026",
        "publishDateTo": "08.08.2026",
    }
    with pytest.raises(ValueError, match="31 days"):
        EisRssQuery(
            published_from=date(2026, 1, 1),
            published_to=date(2026, 8, 8),
            limit=1,
        )


def test_eis_rss_rejects_entities_but_accepts_a_valid_empty_result() -> None:
    with pytest.raises(SourceContractError, match="DTD or ENTITY"):
        parse_eis_rss(
            b'<!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss>&xxe;</rss>',
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            ingestion_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            limit=10,
        )
    records = parse_eis_rss(
        b'<rss version="2.0"><channel><title>empty</title></channel></rss>',
        observed_at=datetime(2026, 8, 8, tzinfo=UTC),
        ingestion_run_id=UUID("00000000-0000-0000-0000-000000000001"),
        limit=10,
    )

    assert records == ()

    with pytest.raises(SourceContractError, match="DTD or ENTITY"):
        parse_eis_rss(
            b" " * 5000
            + b'<!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><rss>&xxe;</rss>',
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            ingestion_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            limit=10,
        )


def test_eis_rss_rejects_a_missing_channel() -> None:
    with pytest.raises(SourceContractError, match="missing channel"):
        parse_eis_rss(
            b'<rss version="2.0" />',
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            ingestion_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            limit=10,
        )


def test_eis_rss_rejects_item_links_outside_the_official_host() -> None:
    raw = (
        (FIXTURES / "eis_search_rss.xml")
        .read_bytes()
        .replace(
            b"https://zakupki.gov.ru/",
            b"https://untrusted.example/",
            1,
        )
    )

    with pytest.raises(SourceContractError, match="outside the official host"):
        parse_eis_rss(
            raw,
            observed_at=datetime(2026, 8, 8, tzinfo=UTC),
            ingestion_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            limit=10,
        )
