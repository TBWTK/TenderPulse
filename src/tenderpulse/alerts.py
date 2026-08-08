from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from tenderpulse.alert_models import AlertView
from tenderpulse.domain.matching import MatchDecision, TenderMatcher
from tenderpulse.domain.models import LifecycleStatus, RecordKind
from tenderpulse.persistence.alert_repository import AlertRepository
from tenderpulse.persistence.repository import ProcurementRepository


class AlertService:
    def __init__(self, session: Session, *, now: Callable[[], datetime]) -> None:
        self._session = session
        self._now = now

    def sync_profile(self, profile_slug: str) -> tuple[AlertView, ...]:
        records = ProcurementRepository(self._session)
        profile = records.get_profile(profile_slug)
        if profile is None:
            raise LookupError(f"company profile not found: {profile_slug}")
        opportunities = tuple(
            record
            for record in records.list_current_records()
            if record.kind is RecordKind.NOTICE
            and record.lifecycle in {LifecycleStatus.ACTIVE, LifecycleStatus.PLANNED}
        )
        ranked = TenderMatcher(now=self._now).rank(profile, opportunities)
        record_by_key = {
            (record.source, record.source_record_id): record for record in opportunities
        }
        alerts = AlertRepository(self._session)
        created: list[AlertView] = []
        at = self._now()
        for recommendation in ranked:
            if recommendation.decision is not MatchDecision.RECOMMENDED:
                continue
            record = record_by_key[(recommendation.record_source, recommendation.record_source_id)]
            alert = alerts.add_recommendation(profile, record, recommendation, at=at)
            if alert is not None:
                created.append(alert)
        return tuple(created)

    def sync_all(self) -> tuple[AlertView, ...]:
        profiles = ProcurementRepository(self._session).list_profiles()
        return tuple(alert for profile in profiles for alert in self.sync_profile(profile.slug))
