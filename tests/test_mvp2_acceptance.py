from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.api import create_app
from tenderpulse.bootstrap import seed_demo
from tenderpulse.domain.matching import BlockerCode, MatchDecision, TenderMatcher
from tenderpulse.persistence.models import Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.raw_store import MemoryRawStore

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _workspace():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    raw_store = MemoryRawStore()
    seed_demo(factory, raw_store, now=lambda: NOW)
    return factory, raw_store


def _profile(repository: ProcurementRepository, slug: str):
    profile = repository.get_profile(slug)
    assert profile is not None
    return profile


def test_seeded_russian_vertical_slice_covers_four_sectors_and_geography() -> None:
    factory, _raw_store = _workspace()
    with factory() as session:
        repository = ProcurementRepository(session)
        records = {record.source_record_id: record for record in repository.list_current_records()}
        matcher = TenderMatcher(now=lambda: NOW)

        auto_profile = _profile(repository, "auto-service-moscow")
        auto_local = matcher.match(auto_profile, records["0123456789026000001"])
        auto_kamchatka = matcher.match(auto_profile, records["0123456789026000002"])
        contractor_profile = _profile(repository, "auto-service-moscow").model_copy(
            update={"version": 2, "contractors_allowed": True}
        )
        auto_with_contractor = matcher.match(contractor_profile, records["0123456789026000002"])
        it_remote = matcher.match(
            _profile(repository, "it-russia-integrator"), records["0123456789026000003"]
        )
        landscaping = matcher.match(
            _profile(repository, "landscaping-moscow"), records["0123456789026000004"]
        )
        cleaning = matcher.match(
            _profile(repository, "cleaning-moscow"), records["0123456789026000005"]
        )

    assert auto_local.decision is MatchDecision.RECOMMENDED
    assert auto_kamchatka.decision is MatchDecision.NOT_RELEVANT
    assert BlockerCode.GEOGRAPHY_OUT_OF_SCOPE in auto_kamchatka.blockers
    assert auto_with_contractor.decision is MatchDecision.REVIEW
    assert any(
        reason.code == "geography_contractor_coverage" for reason in auto_with_contractor.reasons
    )
    assert it_remote.decision is MatchDecision.RECOMMENDED
    assert landscaping.decision is MatchDecision.RECOMMENDED
    assert cleaning.decision is MatchDecision.RECOMMENDED


def test_profile_change_and_fifth_company_survive_reseed_and_use_same_pipeline() -> None:
    factory, raw_store = _workspace()
    client = TestClient(create_app(factory, now=lambda: NOW))
    auto = next(
        item for item in client.get("/api/profiles").json() if item["slug"] == "auto-service-moscow"
    )
    auto["version"] = 2
    auto["contractors_allowed"] = True

    updated = client.put("/api/profiles/auto-service-moscow", json=auto)
    recommendations = client.get("/api/recommendations/auto-service-moscow").json()
    kamchatka = next(
        item for item in recommendations if item["record_source_id"] == "0123456789026000002"
    )
    custom = {
        **auto,
        "slug": "office-furniture",
        "version": 1,
        "name": "Офисная мебель",
        "description": "Поставка столов, шкафов и офисной мебели.",
        "services": ["поставка офисной мебели"],
        "capabilities": ["комплектация административных зданий"],
        "positive_keywords": ["офисная мебель", "стол", "шкаф"],
        "negative_keywords": ["ремонт автомобилей"],
        "classification_prefixes": {"CPV": ["3913"], "OKPD2": ["31.01"]},
        "customer_types": ["государственные учреждения"],
        "contractors_allowed": False,
    }
    created = client.post("/api/profiles", json=custom)
    custom_recommendations = client.get("/api/recommendations/office-furniture").json()

    assert updated.status_code == 200
    assert kamchatka["decision"] == "review"
    assert "geography_contractor_coverage" in {reason["code"] for reason in kamchatka["reasons"]}
    assert created.status_code == 201
    assert (
        next(
            item
            for item in custom_recommendations
            if item["record_source_id"] == "0123456789026000006"
        )["decision"]
        == "recommended"
    )

    seed_demo(factory, raw_store, now=lambda: NOW)
    restarted = TestClient(create_app(factory, now=lambda: NOW))
    profiles = restarted.get("/api/profiles").json()

    assert len(profiles) == 5
    assert next(item for item in profiles if item["slug"] == "auto-service-moscow")["version"] == 2
    assert restarted.get("/api/profiles/office-furniture/history").status_code == 200
    assert restarted.get("/api/recommendations/office-furniture").status_code == 200


class _EnabledEvidenceGenerator:
    def extract_arguments(self, _evidence: str):  # pragma: no cover - GET must not invoke it
        raise AssertionError("dashboard GET must not call the LLM")


def test_seeded_ui_detail_lineage_analytics_outcome_and_rejected_audit_are_coherent() -> None:
    factory, _raw_store = _workspace()
    client = TestClient(
        create_app(factory, now=lambda: NOW, evidence_generator=_EnabledEvidenceGenerator())
    )

    dashboard = client.get("/?profile=auto-service-moscow")
    detail = client.get("/tenders/eis/0123456789026000001?profile=auto-service-moscow")
    lineage = client.get("/api/records/eis/0123456789026000001/lineage")
    analytics = client.get("/api/analytics/product/auto-service-moscow")
    outcomes = client.get("/api/analytics/award-outcomes")

    assert dashboard.status_code == detail.status_code == 200
    actionable, rejected = dashboard.text.split('id="rejected-opportunities"', maxsplit=1)
    assert "Техническое обслуживание и ремонт автомобилей" in actionable
    assert "Ремонт служебных автомобилей в Камчатском крае" in rejected
    assert 'class="button ghost ai-button"' not in rejected
    assert "Открыть на официальном сайте" in detail.text
    assert "https://zakupki.gov.ru/" in detail.text
    assert "Требования и сроки" in detail.text
    assert "не проверено" in detail.text
    assert lineage.json()[0]["record"]["evidence"]["raw_sha256"] in detail.text
    assert lineage.json()[0]["record"]["evidence"]["ingestion_run_id"] in detail.text
    assert analytics.json()["diagnostics"]["geography_rejected"] >= 1
    assert outcomes.json()[0]["supplier_names"] == ["ООО Надёжный автосервис"]
