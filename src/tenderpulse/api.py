from collections.abc import Callable, Generator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

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
from tenderpulse.domain.matching import Recommendation, TenderMatcher, current_opportunities
from tenderpulse.domain.models import ProcurementRecord, SourceCode
from tenderpulse.ingestion_models import IngestionRunView, SourceFreshnessView
from tenderpulse.live_ingestion import LiveSourceResult
from tenderpulse.outcomes import AwardOutcomeView
from tenderpulse.persistence.ai_repository import AIExtractionRepository
from tenderpulse.persistence.alert_repository import AlertRepository
from tenderpulse.persistence.ingestion_repository import IngestionRepository
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.product_analytics import ProductAnalytics, build_product_analytics
from tenderpulse.profiles import CompanyProfile
from tenderpulse.source_policy import current_product_records
from tenderpulse.sources.common import SourceContractError

MAX_EIS_UPLOAD_BYTES = 10 * 1024 * 1024
WORKSPACE_TIMEZONE = ZoneInfo("Europe/Moscow")
RU_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
DECISION_LABELS = {
    "recommended": "Рекомендовано",
    "review": "Нужно проверить",
    "not_relevant": "Не подходит",
    "expired": "Срок истёк",
}
REASON_LABELS = {
    "classification": "совпали классификаторы",
    "keywords": "совпали ключевые слова",
    "budget": "бюджет входит в диапазон",
    "geography_service_region": "регион входит в зону работы",
    "geography_nationwide_remote": "допустимо удалённое выполнение по России",
    "geography_contractor_coverage": "регион покрывается через подрядчика",
    "geography_travel_coverage": "регион покрывается командировкой",
}
DIAGNOSTIC_LABELS = {
    "unknown_amount": "сумма не найдена",
    "unknown_deadline": "срок подачи не найден",
    "unknown_location": "место исполнения не найдено",
    "deadline_passed": "срок подачи истёк",
    "negative_keyword": "обнаружено стоп-слово",
    "geography_out_of_scope": "регион вне зоны работы",
    "geography_excluded": "регион явно исключён",
}
REGION_LABELS = {
    "RU-MOW": "Москва",
    "RU-MOS": "Московская область",
    "RU-KAM": "Камчатский край",
    "RU-PRI": "Приморский край",
}
RUN_STATUS_LABELS = {
    "succeeded": "успешно",
    "running": "выполняется",
    "failed": "ошибка",
    "unknown": "нет данных",
}
LIFECYCLE_LABELS = {
    "planned": "Планируется",
    "active": "Активна",
    "awarded": "Завершена выбором победителя",
    "cancelled": "Отменена",
    "unknown": "Статус не определён",
}
DELIVERY_MODE_LABELS = {
    "onsite": "Физически на объекте",
    "remote": "Удалённо",
    "hybrid": "Гибридно",
    "unknown": "Формат не определён",
}
NAV_ITEMS = (
    ("overview", "/", "Обзор"),
    ("tenders", "/tenders", "Тендеры"),
    ("analytics", "/analytics", "Аналитика"),
    ("companies", "/companies", "Компании"),
    ("data", "/data", "Данные"),
)


@dataclass(frozen=True)
class WebWorkspace:
    repository: ProcurementRepository
    profiles: tuple[CompanyProfile, ...]
    selected: CompanyProfile | None
    records: tuple[ProcurementRecord, ...]
    opportunities: tuple[ProcurementRecord, ...]
    recommendations: tuple[Recommendation, ...]
    lineages: dict[tuple[SourceCode, str], tuple[RecordVersion, ...]]
    award_outcomes: tuple[AwardOutcomeView, ...]
    analytics: ProductAnalytics | None


def _format_amount(value: Decimal | None) -> str:
    if value is None:
        return "—"
    rendered = f"{value:,.2f}"
    if rendered.endswith(".00"):
        rendered = rendered[:-3]
    return rendered.replace(",", " ").replace(".", ",")


class IngestionRunner(Protocol):
    def run_cycle(
        self,
        *,
        limit: int,
        eis_lookback_days: int,
        sources: tuple[SourceCode, ...],
    ) -> tuple[LiveSourceResult, ...]: ...

    def ingest_eis_upload(self, *, raw: bytes, filename: str) -> LiveSourceResult: ...


class ManualIngestionCommand(BaseModel):
    sources: tuple[SourceCode, ...] = (SourceCode.EIS,)
    limit: int = Field(default=25, ge=1, le=50)
    eis_lookback_days: int = Field(default=7, ge=1, le=31)

    @field_validator("sources")
    @classmethod
    def validate_live_sources(cls, sources: tuple[SourceCode, ...]) -> tuple[SourceCode, ...]:
        if not sources:
            raise ValueError("at least one source is required")
        unsupported = set(sources) - {SourceCode.EIS}
        if unsupported:
            raise ValueError("MVP 2.0 live ingestion supports EIS only")
        return tuple(dict.fromkeys(sources))


def create_app(
    session_factory: sessionmaker[Session],
    *,
    now: Callable[[], datetime],
    evidence_generator: EvidenceGenerator | None = None,
    ai_requested_model: str = "GigaChat-2",
    ingestion_runner: IngestionRunner | None = None,
) -> FastAPI:
    app = FastAPI(title="TenderPulse", version="0.2.0")
    web_root = Path(__file__).with_name("web")
    templates = Jinja2Templates(directory=web_root / "templates")
    templates.env.filters["amount"] = _format_amount
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

    @app.post("/api/profiles", response_model=CompanyProfile, status_code=201)
    def create_profile(profile: CompanyProfile, session: SessionDep) -> CompanyProfile:
        repository = ProcurementRepository(session)
        try:
            repository.create_profile(profile)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        session.commit()
        return profile

    @app.get(
        "/api/profiles/{profile_slug}/history",
        response_model=list[CompanyProfile],
    )
    def profile_history(
        profile_slug: str,
        session: SessionDep,
    ) -> tuple[CompanyProfile, ...]:
        history = ProcurementRepository(session).list_profile_history(profile_slug)
        if not history:
            raise HTTPException(status_code=404, detail="company profile not found")
        return history

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
        return current_product_records(ProcurementRepository(session).list_current_records())

    @app.get("/api/recommendations/{profile_slug}", response_model=list[Recommendation])
    def recommendations(
        profile_slug: str,
        session: SessionDep,
    ) -> list[Recommendation]:
        repository = ProcurementRepository(session)
        profile = repository.get_profile(profile_slug)
        if profile is None:
            raise HTTPException(status_code=404, detail="company profile not found")
        opportunities = current_opportunities(repository.list_current_records())
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
        return IngestionRepository(session).list_current_product_runs(limit=limit)

    @app.post("/api/ingestion/run", response_model=list[LiveSourceResult])
    def run_ingestion(command: ManualIngestionCommand) -> tuple[LiveSourceResult, ...]:
        if ingestion_runner is None:
            raise HTTPException(status_code=503, detail="live ingestion is not configured")
        return ingestion_runner.run_cycle(
            sources=command.sources,
            limit=command.limit,
            eis_lookback_days=command.eis_lookback_days,
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

    @app.get(
        "/api/analytics/product/{profile_slug}",
        response_model=ProductAnalytics,
    )
    def product_analytics(profile_slug: str, session: SessionDep) -> ProductAnalytics:
        repository = ProcurementRepository(session)
        profile = repository.get_profile(profile_slug)
        if profile is None:
            raise HTTPException(status_code=404, detail="company profile not found")
        records = current_product_records(repository.list_current_records())
        opportunities = current_opportunities(records)
        ranked = TenderMatcher(now=now).rank(profile, opportunities)
        product_keys = {(record.source, record.source_record_id) for record in records}
        lineages = {
            key: versions
            for key, versions in repository.list_all_lineages().items()
            if key in product_keys
        }
        return build_product_analytics(
            current_records=records,
            opportunities=opportunities,
            recommendations=ranked,
            lineages=lineages,
            award_outcomes=repository.list_award_outcomes(),
            profile=profile,
            as_of=now(),
        )

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

    @app.get(
        "/tenders/{source}/{source_record_id}",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    def tender_detail(
        request: Request,
        source: SourceCode,
        source_record_id: str,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        repository = workspace.repository
        records = workspace.records
        record = next(
            (
                item
                for item in records
                if item.source is source and item.source_record_id == source_record_id
            ),
            None,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="procurement record not found")
        selected = workspace.selected
        recommendation = TenderMatcher(now=now).match(selected, record) if selected else None
        attempts = AIExtractionRepository(session).list_attempts(source, source_record_id)
        record_codes = {(item.system, item.code) for item in record.classifications}
        related_outcomes = tuple(
            outcome
            for outcome in repository.list_award_outcomes()
            if outcome.buyer_name == record.buyer_name
            or bool(
                record_codes
                & {
                    (item.system, item.code)
                    for candidate in records
                    if candidate.source is outcome.record_source
                    and candidate.source_record_id == outcome.record_source_id
                    for item in candidate.classifications
                }
            )
        )
        context = _web_context(workspace, active_page="tenders", now=now)
        context.update(
            {
                "record": record,
                "recommendation": recommendation,
                "evidence_attempt": attempts[-1] if attempts else None,
                "lineage": repository.lineage(source, source_record_id),
                "related_outcomes": related_outcomes,
                "ai_enabled": evidence_generator is not None,
            }
        )
        return templates.TemplateResponse(
            request=request,
            name="tender_detail.html",
            context=context,
        )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def overview(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        context = _web_context(workspace, active_page="overview", now=now)
        actionable = tuple(
            item
            for item in workspace.recommendations
            if item.decision.value in {"recommended", "review"}
        )
        alerts = (
            AlertRepository(session).list_for_profile(workspace.selected.slug)
            if workspace.selected
            else ()
        )
        context.update(
            {
                "record_count": len(workspace.records),
                "opportunity_count": len(workspace.opportunities),
                "actionable_count": len(actionable),
                "recommended_count": sum(
                    item.decision.value == "recommended" for item in actionable
                ),
                "rejected_count": len(workspace.recommendations) - len(actionable),
                "unread_alert_count": sum(alert.read_at is None for alert in alerts),
                "analytics": workspace.analytics,
                "freshness": IngestionRepository(session).source_freshness(now=now()),
            }
        )
        return templates.TemplateResponse(
            request=request,
            name="overview.html",
            context=context,
        )

    @app.get("/tenders", response_class=HTMLResponse, include_in_schema=False)
    def tenders(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
        search: str = "",
        decision: str = "all",
        region: str = "all",
        sort: str = "relevance",
    ) -> HTMLResponse:
        allowed_decisions = {
            "all",
            "actionable",
            "recommended",
            "review",
            "rejected",
            "not_relevant",
            "expired",
        }
        allowed_sorts = {"relevance", "deadline", "region", "amount", "source"}
        if decision not in allowed_decisions:
            raise HTTPException(status_code=422, detail="unsupported decision filter")
        if sort not in allowed_sorts:
            raise HTTPException(status_code=422, detail="unsupported opportunity sort")
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        filtered_opportunities = _filter_opportunities(
            workspace.opportunities,
            search=search,
            region=region,
        )
        filtered_keys = {record.natural_key for record in filtered_opportunities}
        ranked = [
            item
            for item in workspace.recommendations
            if f"{item.record_source.value}:{item.record_source_id}" in filtered_keys
            and _decision_matches(item.decision.value, decision)
        ]
        record_by_key = {
            (record.source, record.source_record_id): record for record in workspace.opportunities
        }
        ranked = _sort_recommendations(ranked, record_by_key, sort=sort)
        extraction_repository = AIExtractionRepository(session)
        actionable_cards: list[dict[str, object]] = []
        rejected_cards: list[dict[str, object]] = []
        for recommendation in ranked:
            record = record_by_key[(recommendation.record_source, recommendation.record_source_id)]
            attempts = extraction_repository.list_attempts(
                record.source,
                record.source_record_id,
            )
            card: dict[str, object] = {
                "recommendation": recommendation,
                "record": record,
                "evidence_attempt": attempts[-1] if attempts else None,
                "lineage": workspace.lineages[(record.source, record.source_record_id)],
            }
            target = (
                actionable_cards
                if recommendation.decision.value in {"recommended", "review"}
                else rejected_cards
            )
            target.append(card)
        context = _web_context(workspace, active_page="tenders", now=now)
        context.update(
            {
                "actionable_cards": actionable_cards,
                "rejected_cards": rejected_cards,
                "opportunity_count": len(workspace.opportunities),
                "recommended_count": sum(
                    recommendation.decision.value == "recommended"
                    for recommendation in workspace.recommendations
                ),
                "available_regions": sorted(
                    {code for record in workspace.opportunities for code in record.region_codes}
                ),
                "filters": {
                    "search": search,
                    "decision": decision,
                    "region": region,
                    "sort": sort,
                },
                "ai_enabled": evidence_generator is not None,
                "alerts": (
                    AlertRepository(session).list_for_profile(workspace.selected.slug)
                    if workspace.selected
                    else ()
                ),
            }
        )
        return templates.TemplateResponse(request=request, name="tenders.html", context=context)

    @app.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
    def analytics_page(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        context = _web_context(workspace, active_page="analytics", now=now)
        context.update(
            {
                "analytics": workspace.analytics,
                "award_outcomes": workspace.award_outcomes[:5],
            }
        )
        return templates.TemplateResponse(
            request=request,
            name="analytics.html",
            context=context,
        )

    @app.get("/companies", response_class=HTMLResponse, include_in_schema=False)
    def companies_page(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        context = _web_context(workspace, active_page="companies", now=now)
        return templates.TemplateResponse(
            request=request,
            name="companies.html",
            context=context,
        )

    @app.get("/companies/new", response_class=HTMLResponse, include_in_schema=False)
    def company_new_page(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        context = _web_context(workspace, active_page="companies", now=now)
        return templates.TemplateResponse(
            request=request,
            name="company_new.html",
            context=context,
        )

    @app.get(
        "/companies/{profile_slug}",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    def company_detail_page(
        request: Request,
        profile_slug: str,
        session: SessionDep,
    ) -> HTMLResponse:
        repository = ProcurementRepository(session)
        if repository.get_profile(profile_slug) is None:
            raise HTTPException(status_code=404, detail="company profile not found")
        workspace = _load_web_workspace(session, profile_slug=profile_slug, now=now)
        context = _web_context(workspace, active_page="companies", now=now)
        context.update(
            {
                "profile_history": repository.list_profile_history(profile_slug),
            }
        )
        return templates.TemplateResponse(
            request=request,
            name="company_detail.html",
            context=context,
        )

    @app.get("/data", response_class=HTMLResponse, include_in_schema=False)
    def data_page(
        request: Request,
        session: SessionDep,
        profile: str | None = None,
    ) -> HTMLResponse:
        workspace = _load_web_workspace(session, profile_slug=profile, now=now)
        context = _web_context(workspace, active_page="data", now=now)
        context.update(
            {
                "freshness": IngestionRepository(session).source_freshness(now=now()),
                "runs": IngestionRepository(session).list_current_product_runs(limit=12),
            }
        )
        return templates.TemplateResponse(request=request, name="data.html", context=context)

    return app


def _format_workspace_date(value: datetime) -> str:
    local_value = value.astimezone(WORKSPACE_TIMEZONE)
    return f"{local_value.day} {RU_MONTHS[local_value.month - 1]} {local_value.year}"


def _load_web_workspace(
    session: Session,
    *,
    profile_slug: str | None,
    now: Callable[[], datetime],
) -> WebWorkspace:
    repository = ProcurementRepository(session)
    profiles = repository.list_profiles()
    selected = repository.get_profile(profile_slug) if profile_slug is not None else None
    if selected is None and profiles:
        selected = profiles[0]
    records = current_product_records(repository.list_current_records())
    opportunities = current_opportunities(records)
    recommendations = tuple(
        TenderMatcher(now=now).rank(selected, opportunities) if selected else ()
    )
    product_keys = {(record.source, record.source_record_id) for record in records}
    lineages = {
        key: versions
        for key, versions in repository.list_all_lineages().items()
        if key in product_keys
    }
    award_outcomes = repository.list_award_outcomes()
    analytics = (
        build_product_analytics(
            current_records=records,
            opportunities=opportunities,
            recommendations=list(recommendations),
            lineages=lineages,
            award_outcomes=award_outcomes,
            profile=selected,
            as_of=now(),
        )
        if selected
        else None
    )
    return WebWorkspace(
        repository=repository,
        profiles=profiles,
        selected=selected,
        records=records,
        opportunities=opportunities,
        recommendations=recommendations,
        lineages=lineages,
        award_outcomes=award_outcomes,
        analytics=analytics,
    )


def _web_context(
    workspace: WebWorkspace,
    *,
    active_page: str,
    now: Callable[[], datetime],
) -> dict[str, object]:
    return {
        "active_page": active_page,
        "nav_items": NAV_ITEMS,
        "profiles": workspace.profiles,
        "selected": workspace.selected,
        "workspace_date": _format_workspace_date(now()),
        "decision_labels": DECISION_LABELS,
        "reason_labels": REASON_LABELS,
        "diagnostic_labels": DIAGNOSTIC_LABELS,
        "region_labels": REGION_LABELS,
        "run_status_labels": RUN_STATUS_LABELS,
        "lifecycle_labels": LIFECYCLE_LABELS,
        "delivery_mode_labels": DELIVERY_MODE_LABELS,
    }


def _filter_opportunities(
    records: tuple[ProcurementRecord, ...],
    *,
    search: str,
    region: str,
) -> tuple[ProcurementRecord, ...]:
    query = " ".join(search.split()).casefold()
    return tuple(
        record
        for record in records
        if (
            not query
            or query
            in " ".join(
                (
                    record.source_record_id,
                    record.title,
                    record.description,
                    record.buyer_name or "",
                )
            ).casefold()
        )
        and (region == "all" or region in record.region_codes)
    )


def _decision_matches(value: str, selected: str) -> bool:
    if selected == "all":
        return True
    if selected == "actionable":
        return value in {"recommended", "review"}
    if selected == "rejected":
        return value in {"not_relevant", "expired"}
    return value == selected


def _sort_recommendations(
    recommendations: list[Recommendation],
    records: dict[tuple[SourceCode, str], ProcurementRecord],
    *,
    sort: str,
) -> list[Recommendation]:
    if sort == "relevance":
        return recommendations

    def record_for(item: Recommendation) -> ProcurementRecord:
        return records[(item.record_source, item.record_source_id)]

    if sort == "deadline":

        def deadline_key(item: Recommendation) -> tuple[bool, float, str]:
            deadline = record_for(item).deadline_at
            return (
                deadline is None,
                deadline.timestamp() if deadline is not None else float("inf"),
                item.record_source_id,
            )

        return sorted(
            recommendations,
            key=deadline_key,
        )
    if sort == "region":
        return sorted(
            recommendations,
            key=lambda item: (record_for(item).region_codes or ("ZZZ",), item.record_source_id),
        )
    if sort == "amount":
        return sorted(
            recommendations,
            key=lambda item: (
                (_record_amount(record_for(item)) is None),
                -(_record_amount(record_for(item)) or Decimal("0")),
                item.record_source_id,
            ),
        )
    return sorted(
        recommendations,
        key=lambda item: (item.record_source.value, item.record_source_id),
    )


def _record_amount(record: ProcurementRecord) -> Decimal | None:
    return next((lot.amount for lot in record.lots if lot.amount is not None), None)
