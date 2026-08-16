from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.api import create_app
from tenderpulse.auth import AuthService, LocalAccountSeed, seed_local_accounts
from tenderpulse.domain.matching import MatchDecision, Recommendation
from tenderpulse.human_reviews import (
    MAX_HUMAN_REVIEW_SHORTLIST,
    HumanReviewCandidate,
    HumanReviewConflict,
    HumanReviewLabel,
    HumanReviewReason,
    HumanReviewSubmission,
    build_human_review_shortlist,
)
from tenderpulse.persistence.human_review_repository import HumanReviewRepository
from tenderpulse.persistence.models import AccountRow, Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles

CLEANING_CODE = "tp_local_cleaning_1234567890abcdef1234567890"
OFFICE_CODE = "tp_local_office_1234567890abcdef123456789012"
PEPPER = SecretStr("review-test-pepper-1234567890-abcdef")


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def _seed(factory: sessionmaker[Session], record, *, now: datetime) -> None:
    with factory.begin() as session:
        ProcurementRepository(session).seed_profiles(load_demo_profiles())
        ProcurementRepository(session).apply_records((record,), at=now)
        seed_local_accounts(
            session,
            (
                LocalAccountSeed(
                    slug="cleaning-demo",
                    display_name="Чистая территория",
                    profile_slug="cleaning-moscow",
                    access_code=SecretStr(CLEANING_CODE),
                ),
                LocalAccountSeed(
                    slug="office-demo",
                    display_name="Офисное снабжение",
                    profile_slug="office-supply-moscow",
                    access_code=SecretStr(OFFICE_CODE),
                ),
            ),
            pepper=PEPPER,
            now=lambda: now,
        )


def _client(factory: sessionmaker[Session], *, now: datetime) -> TestClient:
    auth = AuthService(
        factory,
        pepper=PEPPER,
        now=lambda: now,
        session_ttl=timedelta(hours=12),
        secure_cookie=False,
    )
    return TestClient(create_app(factory, now=lambda: now, auth_service=auth))


def _login(client: TestClient, code: str) -> None:
    response = client.post("/login", data={"access_code": code}, follow_redirects=False)
    assert response.status_code == 303


def _submission(record, *, latest: int | None = None) -> HumanReviewSubmission:
    return HumanReviewSubmission(
        profile_version=1,
        record_version=1,
        raw_sha256=record.evidence.raw_sha256,
        expected_latest_revision=latest,
        label=HumanReviewLabel.RELEVANT,
        reason=HumanReviewReason.SCOPE,
        note="Предмет закупки соответствует услугам компании.",
    )


def test_repository_appends_immutable_review_revisions(cleaning_notice) -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    factory = _factory()
    _seed(factory, cleaning_notice, now=now)

    with factory.begin() as session:
        account = session.query(AccountRow).filter_by(slug="cleaning-demo").one()
        repository = HumanReviewRepository(session)
        first = repository.append(
            account_id=account.id,
            profile_slug="cleaning-moscow",
            source=cleaning_notice.source,
            source_record_id=cleaning_notice.source_record_id,
            submission=_submission(cleaning_notice),
            at=now,
        )
        second = repository.append(
            account_id=account.id,
            profile_slug="cleaning-moscow",
            source=cleaning_notice.source,
            source_record_id=cleaning_notice.source_record_id,
            submission=_submission(cleaning_notice, latest=1).model_copy(
                update={
                    "label": HumanReviewLabel.INSUFFICIENT_EVIDENCE,
                    "reason": HumanReviewReason.QUALIFICATION,
                    "note": "Нужно подтвердить исполненный договор и акты.",
                }
            ),
            at=now + timedelta(minutes=1),
        )
        history = repository.list_for_account(account.id)

    assert (first.revision, second.revision) == (1, 2)
    assert [item.label for item in history] == [
        HumanReviewLabel.RELEVANT,
        HumanReviewLabel.INSUFFICIENT_EVIDENCE,
    ]
    assert second.supersedes_id == first.id


@pytest.mark.parametrize(
    "update",
    [
        {"profile_version": 99},
        {"record_version": 99},
        {"raw_sha256": "0" * 64},
        {"expected_latest_revision": 1},
    ],
)
def test_repository_rejects_stale_or_concurrent_review_identity(cleaning_notice, update) -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    factory = _factory()
    _seed(factory, cleaning_notice, now=now)

    with factory.begin() as session:
        account = session.query(AccountRow).filter_by(slug="cleaning-demo").one()
        with pytest.raises(HumanReviewConflict):
            HumanReviewRepository(session).append(
                account_id=account.id,
                profile_slug="cleaning-moscow",
                source=cleaning_notice.source,
                source_record_id=cleaning_notice.source_record_id,
                submission=_submission(cleaning_notice).model_copy(update=update),
                at=now,
            )


def test_authenticated_review_api_is_tenant_scoped_and_requires_csrf(cleaning_notice) -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    factory = _factory()
    _seed(factory, cleaning_notice, now=now)
    cleaning = _client(factory, now=now)
    _login(cleaning, CLEANING_CODE)
    path = f"/api/reviews/{cleaning_notice.source.value}/{cleaning_notice.source_record_id}"

    missing_csrf = cleaning.post(
        path,
        json=_submission(cleaning_notice).model_dump(mode="json"),
    )
    assert missing_csrf.status_code == 403
    csrf = cleaning.cookies.get("tenderpulse_csrf") or ""
    created = cleaning.post(
        path,
        json=_submission(cleaning_notice).model_dump(mode="json"),
        headers={"X-CSRF-Token": csrf},
    )

    assert created.status_code == 201
    assert created.json()["profile_slug"] == "cleaning-moscow"
    assert len(cleaning.get("/api/reviews").json()) == 1

    office = _client(factory, now=now)
    _login(office, OFFICE_CODE)
    assert office.get("/api/reviews").json() == []


def test_review_page_is_blind_and_exposes_exact_evidence_form(cleaning_notice) -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    factory = _factory()
    _seed(factory, cleaning_notice, now=now)
    client = _client(factory, now=now)
    _login(client, CLEANING_CODE)

    response = client.get("/reviews")

    assert response.status_code == 200
    assert "Проверка закупок" in response.text
    assert cleaning_notice.title in response.text
    assert 'name="record_version" value="1"' in response.text
    assert f'name="raw_sha256" value="{cleaning_notice.evidence.raw_sha256}"' in response.text
    assert 'href="/reviews" aria-current="page"' in response.text
    assert "match score" not in response.text.casefold()
    assert "Рекомендовано" not in response.text
    assert "Нужно проверить" not in response.text
    assert "qualification_review_required" not in response.text


def test_human_review_shortlist_is_bounded_and_keeps_blind_controls(cleaning_notice) -> None:
    candidates = tuple(
        HumanReviewCandidate(
            record=cleaning_notice.model_copy(update={"source_record_id": f"review-{index:02d}"}),
            profile_version=1,
            record_version=1,
            raw_sha256=cleaning_notice.evidence.raw_sha256,
            latest_review=None,
        )
        for index in range(20)
    )
    recommendations = tuple(
        Recommendation(
            profile_slug="cleaning-moscow",
            record_source=candidate.record.source,
            record_source_id=candidate.record.source_record_id,
            score=0,
            decision=(MatchDecision.REVIEW if index < 12 else MatchDecision.NOT_RELEVANT),
            reasons=(),
            gaps=(),
        )
        for index, candidate in enumerate(candidates)
    )

    shortlist = build_human_review_shortlist(candidates, recommendations)

    assert len(shortlist) == MAX_HUMAN_REVIEW_SHORTLIST == 15
    assert [item.record.source_record_id for item in shortlist[:10]] == [
        f"review-{index:02d}" for index in range(10)
    ]
    assert [item.record.source_record_id for item in shortlist[10:]] == [
        f"review-{index:02d}" for index in range(12, 17)
    ]
