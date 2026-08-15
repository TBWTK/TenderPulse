from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from zipfile import BadZipFile, ZipFile

from tenderpulse.domain.geography import ServiceDeliveryMode
from tenderpulse.domain.models import (
    ClassificationCode,
    LifecycleStatus,
    Lot,
    ProcurementRecord,
    RecordKind,
    SourceCode,
    SourceEvidence,
)
from tenderpulse.sources.common import SourceContractError, raw_sha256

_EXPORT_NAMESPACE = "http://zakupki.gov.ru/oos/export/1"
MAX_EIS_PACKAGE_MEMBERS = 50
MAX_EIS_UNCOMPRESSED_BYTES = 20 * 1024 * 1024


def parse_eis_package(
    raw: bytes,
    *,
    ingestion_run_id: UUID,
    observed_at: datetime,
    source_filename: str,
) -> tuple[ProcurementRecord, ...]:
    package_digest = raw_sha256(raw)
    if raw.startswith(b"PK"):
        members = _read_safe_xml_members(raw)
    else:
        if not source_filename.lower().endswith(".xml"):
            raise SourceContractError("EIS manual upload must be an XML or ZIP package")
        members = ((source_filename, raw),)

    records: list[ProcurementRecord] = []
    seen_keys: set[str] = set()
    for member_name, xml in members:
        source_url = (
            f"manual://eis/upload/{quote(source_filename, safe='._-')}/"
            f"{quote(member_name, safe='/._-')}"
        )
        parsed = parse_eis_legacy_xml(
            xml,
            ingestion_run_id=ingestion_run_id,
            observed_at=observed_at,
            source_url=source_url,
        )
        for record in parsed:
            if record.natural_key in seen_keys:
                raise SourceContractError(f"duplicate EIS record in package: {record.natural_key}")
            seen_keys.add(record.natural_key)
            evidence = record.evidence.model_copy(update={"raw_sha256": package_digest})
            records.append(record.model_copy(update={"evidence": evidence}))
            if len(records) > 500:
                raise SourceContractError("EIS package exceeds the 500-record application limit")
    return tuple(records)


def _read_safe_xml_members(raw: bytes) -> tuple[tuple[str, bytes], ...]:
    try:
        with ZipFile(BytesIO(raw)) as archive:
            infos = tuple(info for info in archive.infolist() if not info.is_dir())
            if not infos or len(infos) > MAX_EIS_PACKAGE_MEMBERS:
                raise SourceContractError("EIS ZIP member count is outside the supported range")
            if sum(info.file_size for info in infos) > MAX_EIS_UNCOMPRESSED_BYTES:
                raise SourceContractError("EIS ZIP uncompressed size exceeds the safety limit")
            members: list[tuple[str, bytes]] = []
            for info in infos:
                path = PurePosixPath(info.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
                    raise SourceContractError("EIS ZIP contains an unsafe member path")
                if info.flag_bits & 0x1:
                    raise SourceContractError("encrypted EIS ZIP members are not supported")
                if path.suffix.lower() != ".xml":
                    continue
                members.append((info.filename, archive.read(info)))
    except BadZipFile as error:
        raise SourceContractError("EIS upload is not a valid ZIP package") from error
    if not members:
        raise SourceContractError("EIS ZIP contains no XML members")
    return tuple(members)


def parse_eis_legacy_xml(
    raw: bytes,
    *,
    ingestion_run_id: UUID,
    observed_at: datetime,
    source_url: str,
) -> tuple[ProcurementRecord, ...]:
    upper_prefix = raw[:4096].upper()
    if b"<!DOCTYPE" in upper_prefix or b"<!ENTITY" in upper_prefix:
        raise SourceContractError("EIS XML with DTD or ENTITY declarations is forbidden")
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise SourceContractError("EIS response is not valid XML") from exc

    namespace, local_name = _split_tag(root.tag)
    if namespace != _EXPORT_NAMESPACE or local_name != "export":
        raise SourceContractError("unsupported EIS XML schema family")
    notifications = [
        element for element in root if _split_tag(element.tag)[1] == "fcsNotificationEF"
    ]
    contracts = [element for element in root if _split_tag(element.tag)[1] == "contract"]
    if not notifications and not contracts:
        raise SourceContractError("supported EIS export contains no supported records")

    digest = raw_sha256(raw)
    records = [
        _parse_notification(
            notification,
            digest=digest,
            ingestion_run_id=ingestion_run_id,
            observed_at=observed_at,
            provided_source_url=source_url,
        )
        for notification in notifications
    ]
    records.extend(
        _parse_contract(
            contract,
            digest=digest,
            ingestion_run_id=ingestion_run_id,
            observed_at=observed_at,
            provided_source_url=source_url,
        )
        for contract in contracts
    )
    return tuple(records)


def _parse_notification(
    notification: Element,
    *,
    digest: str,
    ingestion_run_id: UUID,
    observed_at: datetime,
    provided_source_url: str,
) -> ProcurementRecord:
    purchase_number = _required_text(notification, "purchaseNumber")
    title = _required_text(notification, "purchaseObjectInfo")
    requirements = _optional_text(notification, "requirements")
    buyer_name = _nested_text(notification, "customer", "fullName")
    published_at = _parse_aware(_optional_text(notification, "docPublishDate"), purchase_number)
    deadline_at = _parse_aware(_optional_text(notification, "applicationEndDate"), purchase_number)
    classifications = _classifications(notification)
    lots = tuple(
        _notice_lot(
            element,
            title=title,
            record_id=purchase_number,
            deadline_at=deadline_at,
        )
        for element in _elements_by_local_name(notification, "lot")
    ) or (
        Lot(
            source_lot_id="LOT-1",
            title=title,
            deadline_at=deadline_at,
            classifications=classifications,
        ),
    )
    region = _optional_text(notification, "regionCode")
    return ProcurementRecord(
        source=SourceCode.EIS,
        source_record_id=purchase_number,
        kind=RecordKind.NOTICE,
        lifecycle=LifecycleStatus.ACTIVE,
        title=title,
        description=" ".join(value for value in (title, requirements) if value),
        buyer_name=buyer_name,
        supplier_names=(),
        classifications=classifications,
        countries=("RU",),
        region_codes=(region,) if region is not None else (),
        delivery_location=_optional_text(notification, "placeOfDelivery"),
        delivery_mode=_delivery_mode(_optional_text(notification, "deliveryMode"), purchase_number),
        published_at=published_at,
        observed_at=observed_at,
        deadline_at=deadline_at,
        lots=lots,
        evidence=SourceEvidence(
            raw_sha256=digest,
            ingestion_run_id=ingestion_run_id,
            source_url=_notice_source_url(purchase_number, provided_source_url),
        ),
    )


def _parse_contract(
    contract: Element,
    *,
    digest: str,
    ingestion_run_id: UUID,
    observed_at: datetime,
    provided_source_url: str,
) -> ProcurementRecord:
    registry_number = _required_text(contract, "registryNumber")
    title = _required_text(contract, "purchaseObjectInfo")
    amount = _decimal_or_error(_optional_text(contract, "contractPrice"), registry_number)
    currency = _nested_text(contract, "currency", "code") if amount is not None else None
    classifications = _classifications(contract)
    region = _optional_text(contract, "regionCode")
    suppliers = tuple(
        value
        for element in _elements_by_local_name(contract, "supplier")
        if (value := _optional_text(element, "fullName")) is not None
    )
    published_at = _parse_aware(_optional_text(contract, "contractDate"), registry_number)
    return ProcurementRecord(
        source=SourceCode.EIS,
        source_record_id=registry_number,
        kind=RecordKind.AWARD,
        lifecycle=LifecycleStatus.AWARDED,
        title=title,
        description=title,
        buyer_name=_nested_text(contract, "customer", "fullName"),
        supplier_names=suppliers,
        classifications=classifications,
        countries=("RU",),
        region_codes=(region,) if region is not None else (),
        delivery_location=_optional_text(contract, "placeOfDelivery"),
        delivery_mode=ServiceDeliveryMode.ONSITE,
        published_at=published_at,
        observed_at=observed_at,
        deadline_at=None,
        lots=(
            Lot(
                source_lot_id="contract",
                title=title,
                amount=amount,
                currency=currency,
                classifications=classifications,
            ),
        ),
        evidence=SourceEvidence(
            raw_sha256=digest,
            ingestion_run_id=ingestion_run_id,
            source_url=_contract_source_url(registry_number, provided_source_url),
        ),
    )


def _notice_lot(
    element: Element,
    *,
    title: str,
    record_id: str,
    deadline_at: datetime | None,
) -> Lot:
    amount = _decimal_or_error(_optional_text(element, "maxPrice"), record_id)
    currency = _nested_text(element, "currency", "code") if amount is not None else None
    return Lot(
        source_lot_id=_optional_text(element, "lotNumber") or "LOT-1",
        title=title,
        amount=amount,
        currency=currency,
        deadline_at=deadline_at,
        classifications=_classifications(element),
    )


def _classifications(root: Element) -> tuple[ClassificationCode, ...]:
    result: list[ClassificationCode] = []
    seen: set[tuple[str, str]] = set()
    for element in _elements_by_local_name(root, "classification"):
        system = _optional_text(element, "system")
        code = _optional_text(element, "code")
        if system is None or code is None:
            raise SourceContractError("EIS classification requires system and code")
        classification = ClassificationCode(system=system, code=code)
        key = (classification.system, classification.code)
        if key not in seen:
            seen.add(key)
            result.append(classification)
    return tuple(result)


def _delivery_mode(value: str | None, record_id: str) -> ServiceDeliveryMode:
    if value is None:
        return ServiceDeliveryMode.UNKNOWN
    try:
        return ServiceDeliveryMode(value.strip().lower())
    except ValueError as error:
        raise SourceContractError(f"EIS record {record_id} has invalid deliveryMode") from error


def _notice_source_url(purchase_number: str, provided: str) -> str:
    if provided.startswith("https://zakupki.gov.ru/") and purchase_number in provided:
        return provided
    return (
        "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html"
        f"?regNumber={purchase_number}"
    )


def _contract_source_url(registry_number: str, provided: str) -> str:
    if provided.startswith("https://zakupki.gov.ru/") and registry_number in provided:
        return provided
    return (
        "https://zakupki.gov.ru/epz/contract/contractCard/common-info.html"
        f"?reestrNumber={registry_number}"
    )


def _split_tag(tag: str) -> tuple[str | None, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return None, tag


def _elements_by_local_name(root: Element, name: str) -> list[Element]:
    return [element for element in root.iter() if _split_tag(element.tag)[1] == name]


def _optional_text(root: Element, name: str) -> str | None:
    for element in _elements_by_local_name(root, name):
        if element.text and element.text.strip():
            return element.text.strip()
    return None


def _nested_text(root: Element, container_name: str, name: str) -> str | None:
    containers = _elements_by_local_name(root, container_name)
    return _optional_text(containers[0], name) if containers else None


def _required_text(root: Element, name: str) -> str:
    value = _optional_text(root, name)
    if value is None:
        raise SourceContractError(f"EIS notification is missing {name}")
    return value


def _parse_aware(value: str | None, purchase_number: str) -> datetime | None:
    if value is None:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceContractError(
            f"EIS notice {purchase_number} has invalid docPublishDate"
        ) from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise SourceContractError(f"EIS notice {purchase_number} docPublishDate has no timezone")
    return result


def _decimal_or_error(value: str | None, purchase_number: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise SourceContractError(f"EIS notice {purchase_number} has invalid maxPrice") from exc
