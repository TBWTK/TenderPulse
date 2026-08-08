from collections import Counter
from collections.abc import Callable, Generator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tenderpulse.ai.models import ExtractionOutcome
from tenderpulse.ai.service import AIExtractionService, EvidenceGenerator
from tenderpulse.alert_models import AlertView
from tenderpulse.alerts import AlertService
from tenderpulse.domain.history import RecordVersion
from tenderpulse.domain.matching import Recommendation, TenderMatcher
from tenderpulse.domain.models import LifecycleStatus, ProcurementRecord, RecordKind, SourceCode
from tenderpulse.ingestion_models import IngestionRunView, SourceFreshnessView
from tenderpulse.live_ingestion import LiveSourceResult
from tenderpulse.outcomes import AwardOutcomeView
from tenderpulse.persistence.ai_repository import AIExtractionRepository
from tenderpulse.persistence.alert_repository import AlertRepository
from tenderpulse.persistence.ingestion_repository import IngestionRepository
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import CompanyProfile
from tenderpulse.sources.common import SourceContractError

MAX_EIS_UPLOAD_BYTES = 10 * 1024 * 1024


class IngestionRunner(Protocol):
    def run_cycle(
        self,
        *,
        limit: int,
        ted_lookback_days: int,
        usa_lookback_days: int,
        sources: tuple[SourceCode, ...],
    ) -> tuple[LiveSourceResult, ...]: ...

    def ingest_eis_upload(self, *, raw: bytes, filename: str) -> LiveSourceResult: ...


class ManualIngestionCommand(BaseModel):
    sources: tuple[SourceCode, ...] = (SourceCode.TED, SourceCode.USA_SPENDING)
    limit: int = Field(default=100, ge=1, le=500)
    ted_lookback_days: int = Field(default=14, ge=1, le=90)
    usa_lookback_days: int = Field(default=365, ge=1, le=731)

    @field_validator("sources")
    @classmethod
    def validate_live_sources(cls, sources: tuple[SourceCode, ...]) -> tuple[SourceCode, ...]:
        if not sources:
            raise ValueError("at least one source is required")
        unsupported = set(sources) - {SourceCode.TED, SourceCode.USA_SPENDING}
        if unsupported:
            raise ValueError("live ingestion supports TED and USAspending only")
        return tuple(dict.fromkeys(sources))


def create_app(
    session_factory: sessionmaker[Session],
    *,
    now: Callable[[], datetime],
    evidence_generator: EvidenceGenerator | None = None,
    ai_requested_model: str = "GigaChat-2",
    ingestion_runner: IngestionRunner | None = None,
) -> FastAPI:
    app = FastAPI(title="TenderPulse", version="0.1.0")
    web_root = Path(__file__).with_name("web")
    templates = Jinja2Templates(directory=web_root / "templates")
    app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")

    def get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    SessionDep = Annotated[Session, Depends(get_session)]

    @app.get("/api/health")
    def health(session: SessionDep) -> dict[str, str]:
        session.execute(select(1))
        return {"status": "ok"}

    @app.get("/api/profiles", response_model=list[CompanyProfile])
    def profiles(session: SessionDep) -> tuple[CompanyProfile, ...]:
        return ProcurementRepository(session).list_profiles()

    @app.put("/api/profiles/{profile_slug}", response_model=CompanyProfile)
    def update_profile(
        profile_slug: str,
        profile: CompanyProfile,
        session: SessionDep,
    ) -> CompanyProfile:
        if profile.slug != profile_slug:
            raise HTTPException(status_code=409, detail="profile slug does not match route")
        repository = ProcurementRepository(session)
        if repository.get_profile(profile_slug) is None:
            raise HTTPException(status_code=404, detail="company profile not found")
        try:
            repository.add_profile_version(profile)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        session.commit()
        return profile

    @app.get("/api/records", response_model=list[ProcurementRecord])
    def records(session: SessionDep) -> tuple[ProcurementRecord, ...]:
        return ProcurementRepository(session).list_current_records()

    @app.get("/api/recommendations/{profile_slug}", response_model=list[Recommendation])
    def recommendations(
        profile_slug: str,
        session: SessionDep,
    ) -> list[Recommendation]:
        repository = ProcurementRepository(session)
        profile = repository.get_profile(profile_slug)
        if profile is None:
            raise HTTPException(status_code=404, detail="company profile not found")
        opportunities = [
            record
            for record in repository.list_current_records()
            if record.kind is RecordKind.NOTICE
            and record.lifecycle in {LifecycleStatus.ACTIVE, LifecycleStatus.PLANNED}
        ]
        return TenderMatcher(now=now).rank(profile, opportunities)

    @app.get(
        "/api/records/{source}/{source_record_id}/lineage",
        response_model=list[RecordVersion],
    )
    def lineage(
        source: SourceCode,
        source_record_id: str,
        session: SessionDep,
    ) -> tuple[RecordVersion, ...]:
        versions = ProcurementRepository(session).lineage(source, source_record_id)
        if not versions:
            raise HTTPException(status_code=404, detail="procurement record not found")
        return versions

    @app.get(
        "/api/records/{source}/{source_record_id}/evidence",
        response_model=list[ExtractionOutcome],
    )
    def evidence_attempts(
        source: SourceCode,
        source_record_id: str,
        session: SessionDep,
    ) -> tuple[ExtractionOutcome, ...]:
        repository = AIExtractionRepository(session)
        if repository.get_current_context(source, source_record_id) is None:
            raise HTTPException(status_code=404, detail="procurement record not found")
        return repository.list_attempts(source, source_record_id)

    @app.post(
        "/api/records/{source}/{source_record_id}/evidence/extract",
        response_model=ExtractionOutcome,
    )
    def extract_evidence(
        source: SourceCode,
        source_record_id: str,
        session: SessionDep,
    ) -> ExtractionOutcome:
        if evidence_generator is None:
            raise HTTPException(
                status_code=503,
                detail="GigaChat evidence extraction is not configured",
            )
        service = AIExtractionService(
            AIExtractionRepository(session),
            evidence_generator,
            requested_model=ai_requested_model,
            now=now,
        )
        try:
            outcome = service.extract(source, source_record_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail="procurement record not found") from error
        session.commit()
        return outcome

    @app.get("/api/ingestion/runs", response_model=list[IngestionRunView])
    def ingestion_runs(
        session: SessionDep,
        limit: int = 50,
    ) -> tuple[IngestionRunView, ...]:
        if not 1 <= limit <= 500:
            raise HTTPException(status_code=422, detail="limit must be between 1 and 500")
        return IngestionRepository(session).list_runs(limit=limit)

    @app.post("/api/ingestion/run", response_model=list[LiveSourceResult])
    def run_ingestion(command: ManualIngestionCommand) -> tuple[LiveSourceResult, ...]:
        if ingestion_runner is None:
            raise HTTPException(status_code=503, detail="live ingestion is not configured")
        return ingestion_runner.run_cycle(
            sources=command.sources,
            limit=command.limit,
            ted_lookback_days=command.ted_lookback_days,
            usa_lookback_days=command.usa_lookback_days,
        )

    @app.post("/api/ingestion/eis-upload", response_model=LiveSourceResult)
    async def upload_eis_package(file: Annotated[UploadFile, File()]) -> LiveSourceResult:
        if ingestion_runner is None:
            raise HTTPException(status_code=503, detail="manual EIS ingestion is not configured")
        filename = file.filename or ""
        if (
            not filename
            or Path(filename).name != filename
            or "\\" in filename
            or Path(filename).suffix.lower() not in {".xml", ".zip"}
        ):
            raise HTTPException(
                status_code=422,
                detail="EIS upload must be a safe .xml or .zip file",
            )
        raw = await file.read(MAX_EIS_UPLOAD_BYTES + 1)
        if not raw or len(raw) > MAX_EIS_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="EIS upload must be between 1 byte and 10 MiB",
            )
        try:
            return ingestion_runner.ingest_eis_upload(raw=raw, filename=filename)
        except SourceContractError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/analytics/source-freshness", response_model=list[SourceFreshnessView])
    def source_freshness(session: SessionDep) -> tuple[SourceFreshnessView, ...]:
        return IngestionRepository(session).source_freshness(now=now())

    @app.get("/api/analytics/award-outcomes", response_model=list[AwardOutcomeView])
    def award_outcomes(session: SessionDep) -> tuple[AwardOutcomeView, ...]:
        return ProcurementRepository(session).list_award_outcomes()

    @app.post("/api/alerts/sync/{profile_slug}", response_model=list[AlertView])
    def sync_alerts(profile_slug: str, session: SessionDep) -> tuple[AlertView, ...]:
        try:
            created = AlertService(session, now=now).sync_profile(profile_slug)
        except LookupError as error:
            raise HTTPException(status_code=404, detail="company profile not found") from error
        session.commit()
        return created

    @app.get("/api/alerts/{profile_slug}", response_model=list[AlertView])
    def alerts(profile_slug: str, session: SessionDep) -> tuple[AlertView, ...]:
        if ProcurementRepository(session).get_profile(profile_slug) is None:
            raise HTTPException(status_code=404, detail="company profile not found")
        return AlertRepository(session).list_for_profile(profile_slug)

    @app.post("/api/alerts/{alert_id}/read", response_model=AlertView)
    def mark_alert_read(alert_id: UUID, session: SessionDep) -> AlertView:
        alert = AlertRepository(session).mark_read(alert_id, at=now())
        if alert is None:
            raise HTTPException(status_code=404, detail="alert not found")
        session.commit()
        return alert

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def dashboard(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        repository = ProcurementRepository(session)
        profiles = repository.list_profiles()
        selected = repository.get_profile(profile) if profile is not None else None
        if selected is None and profiles:
            selected = profiles[0]
        records = repository.list_current_records()
        opportunities = tuple(
            record
            for record in records
            if record.kind is RecordKind.NOTICE
            and record.lifecycle in {LifecycleStatus.ACTIVE, LifecycleStatus.PLANNED}
        )
        ranked = TenderMatcher(now=now).rank(selected, opportunities) if selected else []
        cards = [
            {
                "recommendation": recommendation,
                "record": next(
                    record
                    for record in opportunities
                    if record.source is recommendation.record_source
                    and record.source_record_id == recommendation.record_source_id
                ),
            }
            for recommendation in ranked
        ]
        buyers = Counter(record.buyer_name for record in records if record.buyer_name)
        context = {
            "profiles": profiles,
            "selected": selected,
            "cards": cards,
            "record_count": len(records),
            "opportunity_count": len(opportunities),
            "recommended_count": sum(
                recommendation.decision.value == "recommended" for recommendation in ranked
            ),
            "freshness": IngestionRepository(session).source_freshness(now=now()),
            "runs": IngestionRepository(session).list_runs(limit=6),
            "top_buyers": buyers.most_common(5),
            "award_outcomes": repository.list_award_outcomes()[:5],
            "ai_enabled": evidence_generator is not None,
            "alerts": (
                AlertRepository(session).list_for_profile(selected.slug) if selected else ()
            ),
        }
        return templates.TemplateResponse(request=request, name="dashboard.html", context=context)

    return app
