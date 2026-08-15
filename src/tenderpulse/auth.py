from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tenderpulse.persistence.models import (
    AccessCredentialRow,
    AccountRow,
    CompanyProfileRow,
    WebSessionRow,
)

SESSION_COOKIE = "tenderpulse_session"
CSRF_COOKIE = "tenderpulse_csrf"
CSRF_HEADER = "X-CSRF-Token"


class LocalAccountSeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str = Field(min_length=3, max_length=128, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    display_name: str = Field(min_length=1, max_length=255)
    profile_slug: str = Field(min_length=3, max_length=128)
    access_code: SecretStr
    role: Literal["company", "operator"] = "company"

    @field_validator("access_code")
    @classmethod
    def validate_access_code(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("local access code must contain at least 32 characters")
        return value


class AuthenticatedAccount(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    display_name: str
    role: Literal["company", "operator"]
    profile_slug: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    account: AuthenticatedAccount
    session_token: str
    csrf_token: str
    max_age_seconds: int


def seed_local_accounts(
    session: Session,
    seeds: tuple[LocalAccountSeed, ...],
    *,
    pepper: SecretStr,
    now: Callable[[], datetime],
) -> None:
    if len({seed.slug for seed in seeds}) != len(seeds):
        raise ValueError("local account seeds must have distinct slugs")
    pepper_bytes = _pepper_bytes(pepper)
    seeded_at = now()
    for seed in seeds:
        profile_exists = session.scalar(
            select(CompanyProfileRow.id)
            .where(
                CompanyProfileRow.slug == seed.profile_slug,
                CompanyProfileRow.active.is_(True),
            )
            .limit(1)
        )
        if profile_exists is None:
            raise RuntimeError(f"account profile is missing: {seed.profile_slug}")
        account = session.scalar(select(AccountRow).where(AccountRow.slug == seed.slug))
        if account is None:
            account = AccountRow(
                slug=seed.slug,
                display_name=seed.display_name,
                role=seed.role,
                profile_slug=seed.profile_slug,
                active=True,
                created_at=seeded_at,
                updated_at=seeded_at,
            )
            session.add(account)
            session.flush()
        else:
            account.display_name = seed.display_name
            account.role = seed.role
            account.profile_slug = seed.profile_slug
            account.active = True
            account.updated_at = seeded_at
        code_hash = _keyed_hash(seed.access_code.get_secret_value(), pepper_bytes)
        credential = session.scalar(
            select(AccessCredentialRow).where(AccessCredentialRow.account_id == account.id)
        )
        if credential is None:
            session.add(
                AccessCredentialRow(
                    account_id=account.id,
                    code_prefix=f"sha256:{code_hash[:12]}",
                    code_hash=code_hash,
                    active=True,
                    created_at=seeded_at,
                )
            )
        elif not hmac.compare_digest(credential.code_hash, code_hash):
            credential.code_hash = code_hash
            credential.code_prefix = f"sha256:{code_hash[:12]}"
            credential.active = True
            credential.rotated_at = seeded_at
            for web_session in session.scalars(
                select(WebSessionRow).where(
                    WebSessionRow.account_id == account.id,
                    WebSessionRow.revoked_at.is_(None),
                )
            ):
                web_session.revoked_at = seeded_at


class AuthService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        pepper: SecretStr,
        now: Callable[[], datetime],
        session_ttl: timedelta,
        secure_cookie: bool,
    ) -> None:
        if session_ttl < timedelta(minutes=5) or session_ttl > timedelta(days=30):
            raise ValueError("session TTL must be between 5 minutes and 30 days")
        self._session_factory = session_factory
        self._pepper = _pepper_bytes(pepper)
        self._now = now
        self._session_ttl = session_ttl
        self.secure_cookie = secure_cookie

    @property
    def max_age_seconds(self) -> int:
        return int(self._session_ttl.total_seconds())

    def login(self, access_code: str) -> LoginResult | None:
        code = access_code.strip()
        if not code:
            return None
        code_hash = _keyed_hash(code, self._pepper)
        with self._session_factory.begin() as session:
            row = session.execute(
                select(AccessCredentialRow, AccountRow)
                .join(AccountRow, AccessCredentialRow.account_id == AccountRow.id)
                .where(
                    AccessCredentialRow.code_hash == code_hash,
                    AccessCredentialRow.active.is_(True),
                    AccountRow.active.is_(True),
                )
            ).one_or_none()
            if row is None:
                return None
            credential, account = row
            if not hmac.compare_digest(credential.code_hash, code_hash):
                return None
            now = self._now()
            session_token = secrets.token_urlsafe(32)
            csrf_token = secrets.token_urlsafe(32)
            session.add(
                WebSessionRow(
                    account_id=account.id,
                    token_hash=_keyed_hash(session_token, self._pepper),
                    csrf_hash=_keyed_hash(csrf_token, self._pepper),
                    created_at=now,
                    expires_at=now + self._session_ttl,
                )
            )
            return LoginResult(
                account=_account_view(account),
                session_token=session_token,
                csrf_token=csrf_token,
                max_age_seconds=self.max_age_seconds,
            )

    def resolve(self, session_token: str | None) -> AuthenticatedAccount | None:
        if not session_token:
            return None
        token_hash = _keyed_hash(session_token, self._pepper)
        with self._session_factory.begin() as session:
            row = session.execute(
                select(WebSessionRow, AccountRow)
                .join(AccountRow, WebSessionRow.account_id == AccountRow.id)
                .where(
                    WebSessionRow.token_hash == token_hash,
                    WebSessionRow.revoked_at.is_(None),
                    AccountRow.active.is_(True),
                )
            ).one_or_none()
            if row is None:
                return None
            web_session, account = row
            if _as_utc(web_session.expires_at) <= _as_utc(self._now()):
                web_session.revoked_at = self._now()
                return None
            return _account_view(account)

    def verify_csrf(self, session_token: str | None, csrf_token: str | None) -> bool:
        if not session_token or not csrf_token:
            return False
        token_hash = _keyed_hash(session_token, self._pepper)
        csrf_hash = _keyed_hash(csrf_token, self._pepper)
        with self._session_factory() as session:
            stored = session.scalar(
                select(WebSessionRow.csrf_hash).where(
                    WebSessionRow.token_hash == token_hash,
                    WebSessionRow.revoked_at.is_(None),
                )
            )
        return stored is not None and hmac.compare_digest(stored, csrf_hash)

    def revoke(self, session_token: str | None) -> None:
        if not session_token:
            return
        token_hash = _keyed_hash(session_token, self._pepper)
        with self._session_factory.begin() as session:
            web_session = session.scalar(
                select(WebSessionRow).where(
                    WebSessionRow.token_hash == token_hash,
                    WebSessionRow.revoked_at.is_(None),
                )
            )
            if web_session is not None:
                web_session.revoked_at = self._now()


def _pepper_bytes(pepper: SecretStr) -> bytes:
    value = pepper.get_secret_value()
    if len(value) < 32 or re.fullmatch(r"(?i)(change-me|secret|password|tenderpulse)", value):
        raise ValueError("auth pepper must be a non-default secret of at least 32 characters")
    return value.encode("utf-8")


def _keyed_hash(value: str, pepper: bytes) -> str:
    return hmac.new(pepper, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _account_view(row: AccountRow) -> AuthenticatedAccount:
    role: Literal["company", "operator"]
    if row.role == "company":
        role = "company"
    elif row.role == "operator":
        role = "operator"
    else:
        raise RuntimeError(f"unsupported account role: {row.role}")
    return AuthenticatedAccount(
        id=row.id,
        slug=row.slug,
        display_name=row.display_name,
        role=role,
        profile_slug=row.profile_slug,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
