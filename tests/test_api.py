from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.ai.gigachat import GeneratedArguments
from tenderpulse.api import create_app
from tenderpulse.domain.models import LifecycleStatus, ProcurementRecord, RecordKind, SourceCode
from tenderpulse.live_ingestion import LiveSourceResult
from tenderpulse.persistence.models import Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles


class StubGenerator:
    def extract_arguments(self, evidence: str) -> GeneratedArguments:
        return GeneratedArguments(
            arguments={
                "requirements_status": "found",
                "requirements": [
                    {
                        "text": "Data engineering services are required.",
                        "mandatory": True,
                        "citation": {
                            "field": "description",
                            "quote": "Data engineering",
                        },
                    }
                ],
                "deadlines_status": "found",
                "deadlines": [
                    {
                        "label": "Submission deadline",
                        "value": "2026-09-30T12:00:00Z",
                        "normalized_at": "2026-09-30T12:00:00Z",
                        "citation": {
                            "field": "deadline_at",
                            "quote": "2026-09-30T12:00:00Z",
                        },
                    }
                ],
                "gaps": [],
            },
            response_model="GigaChat-2:fixture",
        )


class StubIngestionRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_cycle(self, **kwargs) -> tuple[LiveSourceResult, ...]:
        self.calls.append(kwargs)
        return (
            LiveSourceResult(
                source=kwargs["sources"][0],
                status="succeeded",
                run_id=UUID("00000000-0000-0000-0000-000000000099"),
                record_count=3,
            ),
        )

    def ingest_eis_upload(self, *, raw: bytes, filename: str) -> LiveSourceResult:
        self.calls.append({"filename": filename, "byte_size": len(raw)})
        return LiveSourceResult(
            source=SourceCode.EIS,
            status="succeeded",
            run_id=UUID("00000000-0000-0000-0000-000000000098"),
            record_count=1,
        )


def _client(
    records: tuple[ProcurementRecord, ...],
    *,
    evidence_generator: StubGenerator | None = None,
    ingestion_runner: StubIngestionRunner | None = None,
    historical_records: tuple[ProcurementRecord, ...] = (),
    now_at: datetime = datetime(2026, 8, 8, tzinfo=UTC),
) -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        repository = ProcurementRepository(session)
        if historical_records:
            repository.apply_records(historical_records, at=datetime(2026, 8, 7, tzinfo=UTC))
        repository.apply_records(records, at=datetime(2026, 8, 8, tzinfo=UTC))
        repository.seed_profiles(load_demo_profiles())
    return TestClient(
        create_app(
            factory,
            now=lambda: now_at,
            evidence_generator=evidence_generator,
            ai_requested_model="GigaChat-2",
            ingestion_runner=ingestion_runner,
        )
    )


def test_health_and_two_profiles_are_exposed(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,))

    assert client.get("/api/health").json() == {"status": "ok"}
    profiles = client.get("/api/profiles")

    assert profiles.status_code == 200
    assert [item["slug"] for item in profiles.json()] == ["it-data-integrator", "medlab-supplier"]


def test_recommendation_api_returns_explanations_and_gaps(
    it_notice: ProcurementRecord,
    medical_notice: ProcurementRecord,
    unrelated_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice, medical_notice, unrelated_notice))

    response = client.get("/api/recommendations/medlab-supplier")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["record_source_id"] == medical_notice.source_record_id
    assert payload[0]["decision"] == "recommended"
    assert payload[0]["reasons"][0]["raw_sha256"] == medical_notice.evidence.raw_sha256
    assert "unknown_deadline" in payload[0]["gaps"]


def test_lineage_api_exposes_version_and_raw_hash(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,))

    response = client.get(
        f"/api/records/{it_notice.source.value}/{it_notice.source_record_id}/lineage"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["version"] == 1
    assert payload[0]["record"]["evidence"]["raw_sha256"] == it_notice.evidence.raw_sha256


def test_unknown_profile_is_404(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,))

    response = client.get("/api/recommendations/missing")

    assert response.status_code == 404


def test_ai_extraction_endpoint_exposes_persisted_citations(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,), evidence_generator=StubGenerator())

    response = client.post(
        f"/api/records/{it_notice.source.value}/{it_notice.source_record_id}/evidence/extract"
    )
    attempts = client.get(
        f"/api/records/{it_notice.source.value}/{it_notice.source_record_id}/evidence"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "validated"
    assert response.json()["claims"]["requirements"][0]["citation"]["quote"] == ("Data engineering")
    assert attempts.status_code == 200
    assert attempts.json() == [response.json()]


def test_ai_extraction_endpoint_is_explicitly_unavailable_without_credentials(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,))

    response = client.post(
        f"/api/records/{it_notice.source.value}/{it_notice.source_record_id}/evidence/extract"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "GigaChat evidence extraction is not configured"


def test_bounded_manual_ingestion_trigger_and_run_projection(it_notice: ProcurementRecord) -> None:
    runner = StubIngestionRunner()
    client = _client((it_notice,), ingestion_runner=runner)

    response = client.post(
        "/api/ingestion/run",
        json={
            "sources": ["ted", "eis"],
            "limit": 25,
            "ted_lookback_days": 10,
            "eis_lookback_days": 3,
            "usa_lookback_days": 30,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["source"] == "ted"
    assert response.json()[0]["record_count"] == 3
    assert runner.calls == [
        {
            "sources": ("ted", "eis"),
            "limit": 25,
            "ted_lookback_days": 10,
            "eis_lookback_days": 3,
            "usa_lookback_days": 30,
        }
    ]
    assert client.get("/api/ingestion/runs").json() == []


def test_manual_ingestion_limit_above_hard_cap_is_rejected(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,), ingestion_runner=StubIngestionRunner())

    response = client.post(
        "/api/ingestion/run",
        json={"sources": ["ted"], "limit": 501},
    )

    assert response.status_code == 422


def test_source_freshness_keeps_missing_runs_explicitly_unknown(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,))

    response = client.get("/api/analytics/source-freshness")

    assert response.status_code == 200
    assert [item["source"] for item in response.json()] == ["ted", "eis", "usaspending"]
    assert all(item["last_status"] == "unknown" for item in response.json())
    assert all(item["last_success_observed_at"] is None for item in response.json())


def test_award_outcome_api_exposes_winner_amount_buyer_and_raw_evidence(
    it_notice: ProcurementRecord,
) -> None:
    award = it_notice.model_copy(
        update={
            "source": SourceCode.USA_SPENDING,
            "source_record_id": "CONT_AWD_001",
            "kind": RecordKind.AWARD,
            "lifecycle": LifecycleStatus.AWARDED,
            "buyer_name": "Department of Health",
            "supplier_names": ("Lab Systems Inc.",),
            "lots": (
                it_notice.lots[0].model_copy(
                    update={"amount": Decimal("125000.50"), "currency": "USD"}
                ),
            ),
            "evidence": it_notice.evidence.model_copy(update={"raw_sha256": "f" * 64}),
        }
    )
    client = _client((award,))

    response = client.get("/api/analytics/award-outcomes")

    assert response.status_code == 200
    assert response.json() == [
        {
            "record_source": "usaspending",
            "record_source_id": "CONT_AWD_001",
            "title": award.title,
            "buyer_name": "Department of Health",
            "supplier_names": ["Lab Systems Inc."],
            "winner_status": "found",
            "amount": "125000.50",
            "currency": "USD",
            "amount_status": "found",
            "observed_at": "2026-08-08T00:00:00Z",
            "raw_sha256": "f" * 64,
            "source_url": award.evidence.source_url,
        }
    ]


def test_full_demo_profile_can_be_versioned_and_changes_recommendations(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,))
    current = next(
        item for item in client.get("/api/profiles").json() if item["slug"] == "it-data-integrator"
    )
    current["version"] = 2
    current.update(
        {
            "name": "  Sovereign   Systems  ",
            "capabilities": [" Secure integration ", "secure integration"],
            "positive_keywords": ["sovereign cloud", " SOVEREIGN CLOUD "],
            "classification_prefixes": {"cpv": ["99-99"]},
            "countries": ["us", "US"],
            "min_amount": "600000",
            "max_amount": "750000",
        }
    )

    updated = client.put("/api/profiles/it-data-integrator", json=current)

    assert updated.status_code == 200
    assert updated.json() == {
        "slug": "it-data-integrator",
        "version": 2,
        "name": "Sovereign Systems",
        "capabilities": ["Secure integration"],
        "positive_keywords": ["sovereign cloud"],
        "classification_prefixes": {"CPV": ["9999"]},
        "countries": ["US"],
        "min_amount": "600000",
        "max_amount": "750000",
    }
    profiles = client.get("/api/profiles").json()
    assert len(profiles) == 2
    recommendation = client.get("/api/recommendations/it-data-integrator").json()[0]
    assert recommendation["score"] == "0"
    assert recommendation["decision"] == "not_relevant"


def test_third_profile_is_rejected(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,))
    current = client.get("/api/profiles").json()[0]
    unknown = {**current, "slug": "third-company", "name": "Third company"}

    rejected = client.put("/api/profiles/third-company", json=unknown)

    assert rejected.status_code == 404


def test_dashboard_renders_product_data(it_notice: ProcurementRecord) -> None:
    client = _client((it_notice,))

    response = client.get("/?profile=it-data-integrator")

    assert response.status_code == 200
    assert "TenderPulse" in response.text
    assert "Northstar Data Integration" in response.text
    assert "Cloud data platform implementation" in response.text
    assert "raw SHA" in response.text
    assert 'name="capabilities"' in response.text
    assert 'name="classifications"' in response.text
    assert 'name="countries"' in response.text
    assert 'name="min_amount"' in response.text
    assert 'name="max_amount"' in response.text
    assert "текущих версий обоих профилей" in response.text


def test_dashboard_workspace_date_comes_from_application_clock(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,), now_at=datetime(2026, 8, 10, tzinfo=UTC))

    response = client.get("/")

    assert response.status_code == 200
    assert "10 августа 2026" in response.text
    assert "08 августа 2026" not in response.text


def test_dashboard_workspace_date_uses_moscow_business_day(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,), now_at=datetime(2026, 8, 9, 21, 30, tzinfo=UTC))

    response = client.get("/")

    assert response.status_code == 200
    assert "10 августа 2026" in response.text


def test_both_demo_profiles_have_distinct_actionable_and_rejected_views(
    it_notice: ProcurementRecord,
    medical_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice, medical_notice))

    for profile, actionable_title, rejected_title in (
        ("it-data-integrator", it_notice.title, medical_notice.title),
        ("medlab-supplier", medical_notice.title, it_notice.title),
    ):
        response = client.get(f"/?profile={profile}")
        actionable, rejected = response.text.split('id="rejected-opportunities"', maxsplit=1)
        actionable = actionable.split('id="actionable-opportunities"', maxsplit=1)[1]

        assert response.status_code == 200
        assert actionable_title in actionable
        assert rejected_title not in actionable
        assert rejected_title in rejected


def test_dashboard_separates_actionable_queue_from_rejected_audit(
    it_notice: ProcurementRecord,
    unrelated_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice, unrelated_notice), evidence_generator=StubGenerator())

    response = client.get("/?profile=it-data-integrator")

    assert response.status_code == 200
    actionable, rejected = response.text.split('id="rejected-opportunities"', maxsplit=1)
    actionable = actionable.split('id="actionable-opportunities"', maxsplit=1)[1]
    assert it_notice.title in actionable
    assert unrelated_notice.title not in actionable
    assert unrelated_notice.title in rejected
    assert "Рассмотрено и отклонено · 1" in response.text
    assert actionable.count('class="button ghost ai-button"') == 1
    assert 'class="button ghost ai-button"' not in rejected
    assert "Проверить требования в доступных данных" in actionable


def test_dashboard_replaces_cached_validated_ai_action_with_coverage_state(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,), evidence_generator=StubGenerator())
    extracted = client.post(
        f"/api/records/{it_notice.source.value}/{it_notice.source_record_id}/evidence/extract"
    )

    response = client.get("/?profile=it-data-integrator")

    assert extracted.status_code == 200
    assert response.status_code == 200
    assert "Проверено по доступным данным" in response.text
    assert 'class="button ghost ai-button"' not in response.text


def test_product_analytics_exposes_exact_current_and_history_scopes(
    it_notice: ProcurementRecord,
    unrelated_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice, unrelated_notice))

    response = client.get("/api/analytics/product/it-data-integrator")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "current_active_or_planned_notices"
    assert payload["decisions"] == {
        "total": 2,
        "recommended": 1,
        "review": 0,
        "not_relevant": 1,
        "expired": 0,
    }
    assert payload["coverage"] == {
        "total": 2,
        "buyer_known": 2,
        "classification_known": 2,
        "geography_known": 2,
        "amount_known": 2,
        "deadline_known": 2,
    }
    assert payload["sources"] == [{"label": "TED", "count": 2}]
    assert payload["categories"] == [
        {"label": "CPV:45000000", "count": 1},
        {"label": "CPV:72200000", "count": 1},
    ]
    assert payload["geographies"] == [
        {"label": "DE", "count": 1},
        {"label": "SE", "count": 1},
    ]
    assert payload["buyers"] == [{"label": "Public Buyer", "count": 2}]
    assert payload["history"] == {
        "current_records": 2,
        "total_versions": 2,
        "changed_records": 0,
    }
    assert payload["outcomes"] == {
        "awards": 0,
        "winner_known": 0,
        "amount_known": 0,
    }


def test_product_analytics_keeps_missing_amount_and_deadline_unknown(
    medical_notice: ProcurementRecord,
) -> None:
    client = _client((medical_notice,))

    response = client.get("/api/analytics/product/medlab-supplier")

    assert response.status_code == 200
    assert response.json()["coverage"]["amount_known"] == 0
    assert response.json()["coverage"]["deadline_known"] == 0


def test_dashboard_renders_version_timeline_and_truthful_analytics_scope(
    it_notice: ProcurementRecord,
) -> None:
    current = it_notice.model_copy(
        update={
            "title": "Corrected cloud platform title",
            "evidence": it_notice.evidence.model_copy(update={"raw_sha256": "d" * 64}),
        }
    )
    client = _client((current,), historical_records=(it_notice,))

    response = client.get("/?profile=it-data-integrator")

    assert response.status_code == 200
    assert "История · 2 версии" in response.text
    assert it_notice.evidence.raw_sha256 in response.text
    assert current.evidence.raw_sha256 in response.text
    assert "Текущий срез active/planned" in response.text
    assert "all history" not in response.text


def test_dashboard_renders_persisted_ai_requirements_deadlines_and_citations(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,), evidence_generator=StubGenerator())
    extraction = client.post(
        f"/api/records/{it_notice.source.value}/{it_notice.source_record_id}/evidence/extract"
    )

    response = client.get("/?profile=it-data-integrator")

    assert extraction.status_code == 200
    assert response.status_code == 200
    assert "requirements: found" in response.text
    assert "Data engineering services are required." in response.text
    assert "deadlines: found" in response.text
    assert "Submission deadline" in response.text
    assert "description · Data engineering" in response.text
    assert "deadline_at · 2026-09-30T12:00:00Z" in response.text


def test_alert_api_syncs_lists_and_marks_in_app_delivery_read(
    it_notice: ProcurementRecord,
) -> None:
    client = _client((it_notice,))

    created = client.post("/api/alerts/sync/it-data-integrator")
    replay = client.post("/api/alerts/sync/it-data-integrator")
    listed = client.get("/api/alerts/it-data-integrator")
    alert_id = created.json()[0]["id"]
    read = client.post(f"/api/alerts/{alert_id}/read")

    assert created.status_code == 200
    assert len(created.json()) == 1
    assert replay.json() == []
    assert listed.json()[0]["raw_sha256"] == it_notice.evidence.raw_sha256
    assert read.status_code == 200
    assert read.json()["read_at"] is not None


def test_manual_eis_xml_upload_is_bounded_and_auditable(it_notice: ProcurementRecord) -> None:
    runner = StubIngestionRunner()
    client = _client((it_notice,), ingestion_runner=runner)
    raw = b"<export>fixture</export>"

    response = client.post(
        "/api/ingestion/eis-upload",
        files={"file": ("notice.xml", raw, "application/xml")},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "eis"
    assert runner.calls == [{"filename": "notice.xml", "byte_size": len(raw)}]
