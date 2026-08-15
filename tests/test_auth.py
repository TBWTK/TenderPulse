from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tenderpulse.api import create_app
from tenderpulse.auth import AuthService, LocalAccountSeed, seed_local_accounts
from tenderpulse.persistence.models import AccessCredentialRow, Base
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import load_demo_profiles

CLEANING_CODE = "tp_local_cleaning_1234567890abcdef1234567890"
OFFICE_CODE = "tp_local_office_1234567890abcdef123456789012"
PEPPER = SecretStr("mvp21-test-pepper-1234567890-abcdef")


def _auth_client() -> tuple[TestClient, sessionmaker, dict[str, datetime]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    clock = {"now": datetime(2026, 8, 16, 12, tzinfo=UTC)}
    with factory.begin() as session:
        ProcurementRepository(session).seed_profiles(load_demo_profiles())
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
            now=lambda: clock["now"],
        )
    auth = AuthService(
        factory,
        pepper=PEPPER,
        now=lambda: clock["now"],
        session_ttl=timedelta(hours=12),
        secure_cookie=False,
    )
    return (
        TestClient(create_app(factory, now=lambda: clock["now"], auth_service=auth)),
        factory,
        clock,
    )


def _login(client: TestClient, code: str) -> None:
    response = client.post("/login", data={"access_code": code}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_unauthenticated_html_redirects_and_api_is_401() -> None:
    client, _, _ = _auth_client()

    page = client.get("/analytics", follow_redirects=False)
    api = client.get("/api/profiles")

    assert page.status_code == 303
    assert page.headers["location"] == "/login?next=%2Fanalytics"
    assert api.status_code == 401
    assert api.json() == {"detail": "authentication required"}

    query_page = client.get(
        "/analytics?profile=cleaning-moscow&window=30d",
        follow_redirects=False,
    )
    assert query_page.headers["location"] == (
        "/login?next=%2Fanalytics%3Fprofile%3Dcleaning-moscow%26window%3D30d"
    )


def test_access_code_creates_revocable_session_without_plaintext_storage() -> None:
    client, factory, _ = _auth_client()

    invalid = client.post("/login", data={"access_code": "wrong"})
    assert invalid.status_code == 401
    assert "Неверный код доступа" in invalid.text

    _login(client, CLEANING_CODE)

    cookie_headers = client.get("/").request.headers.get("cookie", "")
    assert "tenderpulse_session=" in cookie_headers
    assert "tenderpulse_csrf=" in cookie_headers
    with factory() as session:
        credential = session.scalar(select(AccessCredentialRow))
        assert credential is not None
        assert credential.code_hash != CLEANING_CODE
        assert CLEANING_CODE not in credential.code_prefix

    csrf = client.cookies.get("tenderpulse_csrf")
    assert csrf
    logout = client.post(
        "/logout",
        headers={"X-CSRF-Token": csrf},
        follow_redirects=False,
    )
    assert logout.status_code == 303
    assert client.get("/api/profiles").status_code == 401


def test_login_cookie_attributes_match_local_session_contract() -> None:
    client, _, _ = _auth_client()

    response = client.post(
        "/login",
        data={"access_code": CLEANING_CODE},
        follow_redirects=False,
    )
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(item for item in cookies if item.startswith("tenderpulse_session="))
    csrf_cookie = next(item for item in cookies if item.startswith("tenderpulse_csrf="))

    assert "HttpOnly" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=43200" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in csrf_cookie
    assert "Max-Age=43200" in csrf_cookie


def test_company_account_sees_only_own_profile_and_foreign_slug_fails_closed() -> None:
    client, _, _ = _auth_client()
    _login(client, CLEANING_CODE)

    profiles = client.get("/api/profiles")
    own = client.get("/api/recommendations/cleaning-moscow")
    foreign = client.get("/api/recommendations/office-supply-moscow")
    page_foreign = client.get(
        "/analytics?profile=office-supply-moscow",
        follow_redirects=False,
    )

    assert [item["slug"] for item in profiles.json()] == ["cleaning-moscow"]
    assert own.status_code == 200
    assert foreign.status_code == 404
    assert page_foreign.status_code == 404
    assert "profile-switch" not in client.get("/").text
    assert "Чистая территория" in client.get("/").text


def test_company_role_has_no_create_or_operator_surface_and_api_requires_csrf() -> None:
    client, _, _ = _auth_client()
    _login(client, OFFICE_CODE)

    assert client.get("/companies/new", follow_redirects=False).status_code == 403
    assert client.get("/data", follow_redirects=False).status_code == 403
    no_csrf = client.post("/api/alerts/sync/office-supply-moscow")
    assert no_csrf.status_code == 403

    csrf = client.cookies.get("tenderpulse_csrf")
    with_csrf = client.post(
        "/api/alerts/sync/office-supply-moscow",
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert with_csrf.status_code == 200


def test_expired_session_is_rejected() -> None:
    client, _, clock = _auth_client()
    _login(client, CLEANING_CODE)

    clock["now"] += timedelta(hours=13)

    assert client.get("/api/profiles").status_code == 401
