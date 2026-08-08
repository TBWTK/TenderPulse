from __future__ import annotations

import html
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Self
from urllib.parse import parse_qs, urlparse
from uuid import UUID
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tenderpulse.domain.models import (
    LifecycleStatus,
    Lot,
    ProcurementRecord,
    RecordKind,
    SourceCode,
    SourceEvidence,
)
from tenderpulse.sources.common import SourceContractError, raw_sha256

EIS_RSS_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/rss.html"
MAX_EIS_RSS_RECORDS = 50
MAX_EIS_RSS_BYTES = 2 * 1024 * 1024
_PURCHASE_NUMBER_RE = re.compile(r"^\d{19}$")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CURRENCY_CODES = {
    "Российский рубль": "RUB",
    "Доллар США": "USD",
    "Евро": "EUR",
    "RUB": "RUB",
    "USD": "USD",
    "EUR": "EUR",
}
_LIFECYCLE_BY_STAGE = {
    "Подача заявок": LifecycleStatus.ACTIVE,
    "Размещение отменено": LifecycleStatus.CANCELLED,
    "Определение поставщика завершено": LifecycleStatus.AWARDED,
}


class EisRssQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    published_from: date
    published_to: date
    limit: int = Field(default=10, ge=1, le=MAX_EIS_RSS_RECORDS)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.published_to < self.published_from:
            raise ValueError("published_to cannot precede published_from")
        if (self.published_to - self.published_from).days > 31:
            raise ValueError("EIS RSS date window cannot exceed 31 days")
        return self

    def to_params(self) -> dict[str, str]:
        page_size = 10 if self.limit <= 10 else 20 if self.limit <= 20 else 50
        return {
            "fz44": "on",
            "pageNumber": "1",
            "recordsPerPage": f"_{page_size}",
            "sortBy": "UPDATE_DATE",
            "sortDirection": "false",
            "publishDateFrom": self.published_from.strftime("%d.%m.%Y"),
            "publishDateTo": self.published_to.strftime("%d.%m.%Y"),
        }


def parse_eis_rss(
    raw: bytes,
    *,
    ingestion_run_id: UUID,
    observed_at: datetime,
    limit: int,
) -> tuple[ProcurementRecord, ...]:
    if not 1 <= limit <= MAX_EIS_RSS_RECORDS:
        raise ValueError("EIS RSS parser limit must be between 1 and 50")
    if len(raw) > MAX_EIS_RSS_BYTES:
        raise SourceContractError("EIS RSS response exceeds the 2 MiB safety limit")
    upper_raw = raw.upper()
    if b"<!DOCTYPE" in upper_raw or b"<!ENTITY" in upper_raw:
        raise SourceContractError("EIS RSS with DTD or ENTITY declarations is forbidden")
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as error:
        raise SourceContractError("EIS RSS response is not valid XML") from error
    if root.tag != "rss" or root.attrib.get("version") != "2.0":
        raise SourceContractError("unsupported EIS RSS schema")
    channel = root.find("channel")
    if channel is None:
        raise SourceContractError("EIS RSS is missing channel")
    items = channel.findall("item")
    if len(items) > MAX_EIS_RSS_RECORDS:
        raise SourceContractError("EIS RSS exceeds the 50-record safety limit")

    digest = raw_sha256(raw)
    records: list[ProcurementRecord] = []
    seen: set[str] = set()
    for item in items[:limit]:
        item_title = _required_item_text(item, "title")
        source_url = _required_item_text(item, "link")
        source_record_id = _purchase_number(source_url)
        if source_record_id in seen:
            raise SourceContractError(f"duplicate EIS RSS record: {source_record_id}")
        seen.add(source_record_id)
        source_description = _required_item_text(item, "description")
        object_name = _description_field(source_description, "Наименование объекта закупки")
        title = item_title
        if object_name not in {None, "", "null"}:
            assert object_name is not None
            title = object_name
        buyer_name = _optional_item_text(item, "author") or _description_field(
            source_description, "Наименование Заказчика"
        )
        stage = _description_field(source_description, "Этап размещения")
        lifecycle = _LIFECYCLE_BY_STAGE.get(stage or "", LifecycleStatus.UNKNOWN)
        amount_text = _description_field(source_description, "Начальная цена контракта")
        currency_text = _description_field(source_description, "Валюта")
        amount = _amount_or_error(amount_text, source_record_id)
        currency = _CURRENCY_CODES.get(currency_text or "")
        if currency is None:
            amount = None
        published_at = _published_at(_optional_item_text(item, "pubDate"), source_record_id)
        ikz = _description_field(source_description, "Идентификационный код закупки (ИКЗ)")
        description = f"{title}. Этап размещения: {stage or 'unknown'}. ИКЗ: {ikz or 'unknown'}."
        records.append(
            ProcurementRecord(
                source=SourceCode.EIS,
                source_record_id=source_record_id,
                kind=RecordKind.NOTICE,
                lifecycle=lifecycle,
                title=title,
                description=description,
                buyer_name=buyer_name,
                supplier_names=(),
                classifications=(),
                countries=("RU",),
                published_at=published_at,
                observed_at=observed_at,
                deadline_at=None,
                lots=(
                    Lot(
                        source_lot_id="main",
                        title=title,
                        amount=amount,
                        currency=currency,
                        deadline_at=None,
                        classifications=(),
                    ),
                ),
                evidence=SourceEvidence(
                    raw_sha256=digest,
                    ingestion_run_id=ingestion_run_id,
                    source_url=source_url,
                ),
            )
        )
    return tuple(records)


def _purchase_number(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.netloc != "zakupki.gov.ru":
        raise SourceContractError("EIS RSS item link is outside the official host")
    values = parse_qs(parsed.query).get("regNumber", [])
    if len(values) != 1 or not _PURCHASE_NUMBER_RE.fullmatch(values[0]):
        raise SourceContractError("EIS RSS item has an invalid registry number")
    return values[0]


def _description_field(description: str, label: str) -> str | None:
    match = re.search(
        rf"<strong>\s*{re.escape(label)}:\s*</strong>\s*(.*?)(?=<(?:strong|br)\b)",
        description,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    value = html.unescape(_HTML_TAG_RE.sub("", match.group(1))).strip()
    return " ".join(value.split()) or None


def _amount_or_error(value: str | None, source_record_id: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.replace(" ", "").replace(",", "."))
    except InvalidOperation as error:
        raise SourceContractError(
            f"EIS RSS notice {source_record_id} has invalid amount"
        ) from error


def _published_at(value: str | None, source_record_id: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as error:
        raise SourceContractError(
            f"EIS RSS notice {source_record_id} has invalid pubDate"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceContractError(f"EIS RSS notice {source_record_id} pubDate has no timezone")
    return parsed


def _required_item_text(item: ElementTree.Element, name: str) -> str:
    value = _optional_item_text(item, name)
    if value is None:
        raise SourceContractError(f"EIS RSS item is missing {name}")
    return value


def _optional_item_text(item: ElementTree.Element, name: str) -> str | None:
    element = item.find(name)
    if element is None or element.text is None or not element.text.strip():
        return None
    return element.text.strip()
