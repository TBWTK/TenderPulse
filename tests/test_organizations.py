from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.domain.organizations import normalize_organization_name
from tenderpulse.persistence.models import (
    Base,
    OrganizationAliasRow,
    OrganizationRow,
    ProcurementOrganizationLinkRow,
)
from tenderpulse.persistence.repository import ProcurementRepository


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_organization_name_normalization_is_unicode_and_punctuation_stable() -> None:
    assert normalize_organization_name("  PUBLIC—Buyer,  S.p.A. ") == "public buyer s p a"


def test_identity_is_reused_inside_source_but_not_guessed_across_sources(
    it_notice: ProcurementRecord,
) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    same_source_alias = it_notice.model_copy(
        update={
            "source_record_id": "record-2",
            "buyer_name": " PUBLIC—BUYER ",
            "evidence": it_notice.evidence.model_copy(update={"raw_sha256": "d" * 64}),
        }
    )
    other_source = it_notice.model_copy(
        update={
            "source": SourceCode.USA_SPENDING,
            "source_record_id": "award-1",
            "evidence": it_notice.evidence.model_copy(update={"raw_sha256": "e" * 64}),
        }
    )

    repository.apply_records(
        (it_notice, same_source_alias, other_source),
        at=datetime(2026, 8, 8, tzinfo=UTC),
    )
    session.commit()

    organizations = tuple(session.scalars(select(OrganizationRow).order_by(OrganizationRow.source)))
    aliases = tuple(session.scalars(select(OrganizationAliasRow)))
    link_count = session.scalar(select(func.count()).select_from(ProcurementOrganizationLinkRow))

    assert [(row.source, row.normalized_name) for row in organizations] == [
        ("ted", "public buyer"),
        ("usaspending", "public buyer"),
    ]
    assert {row.alias_name for row in aliases} == {"Public Buyer", "PUBLIC—BUYER"}
    assert link_count == 3


def test_organization_links_preserve_version_and_role_evidence(
    it_notice: ProcurementRecord,
) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    at = datetime(2026, 8, 8, tzinfo=UTC)
    awarded = it_notice.model_copy(
        update={"supplier_names": ("Winning Supplier LLC", "Backup Supplier LLC")}
    )

    repository.apply_records((awarded,), at=at)
    session.commit()

    links = tuple(
        session.scalars(
            select(ProcurementOrganizationLinkRow).order_by(
                ProcurementOrganizationLinkRow.role,
                ProcurementOrganizationLinkRow.ordinal,
            )
        )
    )
    assert [(link.role, link.source_name) for link in links] == [
        ("buyer", "Public Buyer"),
        ("supplier", "Winning Supplier LLC"),
        ("supplier", "Backup Supplier LLC"),
    ]
    assert all(link.raw_sha256 == it_notice.evidence.raw_sha256 for link in links)


def test_backfill_repairs_links_for_every_existing_scd2_version(
    it_notice: ProcurementRecord,
) -> None:
    session = _session()
    repository = ProcurementRepository(session)
    first_at = datetime(2026, 8, 8, tzinfo=UTC)
    second_at = datetime(2026, 8, 9, tzinfo=UTC)
    repository.apply_records((it_notice,), at=first_at)
    repository.apply_records(
        (it_notice.model_copy(update={"title": "Corrected title"}),),
        at=second_at,
    )
    session.execute(delete(ProcurementOrganizationLinkRow))
    session.flush()

    created = repository.backfill_organization_links(at=second_at)
    replay = repository.backfill_organization_links(at=second_at)
    session.commit()

    link_count = session.scalar(select(func.count()).select_from(ProcurementOrganizationLinkRow))
    assert created == 2
    assert replay == 0
    assert link_count == 2
