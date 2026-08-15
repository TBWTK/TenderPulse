from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import boto3  # type: ignore[import-untyped]
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from tenderpulse.ai.gigachat import GigaChatClient
from tenderpulse.auth import AuthService, LocalAccountSeed
from tenderpulse.persistence.models import AccountRow
from tenderpulse.persistence.repository import ProcurementRepository
from tenderpulse.profiles import CompanyProfile
from tenderpulse.raw_store import MemoryRawStore, RawStore, S3RawStore
from tenderpulse.settings import Settings
from tenderpulse.sources.http import OfficialSourceClient


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_database(settings: Settings) -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    return engine, sessionmaker(engine, expire_on_commit=False)


def create_profile_provider(
    session_factory: sessionmaker[Session],
) -> Callable[[], tuple[CompanyProfile, ...]]:
    def current_profiles() -> tuple[CompanyProfile, ...]:
        with session_factory() as session:
            return ProcurementRepository(session).list_profiles()

    return current_profiles


def create_account_profile_provider(
    session_factory: sessionmaker[Session],
) -> Callable[[], tuple[CompanyProfile, ...]]:
    def account_profiles() -> tuple[CompanyProfile, ...]:
        with session_factory() as session:
            profile_slugs = tuple(
                dict.fromkeys(
                    session.scalars(
                        select(AccountRow.profile_slug)
                        .where(AccountRow.active.is_(True))
                        .order_by(AccountRow.slug)
                    )
                )
            )
            if not profile_slugs:
                raise RuntimeError("no active account-bound company profiles are configured")
            repository = ProcurementRepository(session)
            profiles: list[CompanyProfile] = []
            for slug in profile_slugs:
                profile = repository.get_profile(slug)
                if profile is None:
                    raise RuntimeError(f"active account profile is unavailable: {slug}")
                profiles.append(profile)
            return tuple(profiles)

    return account_profiles


def create_auth_service(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> AuthService | None:
    if not settings.auth_enabled:
        return None
    if settings.auth_token_pepper is None:
        raise RuntimeError("AUTH_TOKEN_PEPPER is required when AUTH_ENABLED=true")
    return AuthService(
        session_factory,
        pepper=settings.auth_token_pepper,
        now=utc_now,
        session_ttl=timedelta(seconds=settings.auth_session_ttl_seconds),
        secure_cookie=settings.auth_cookie_secure,
    )


def create_local_account_seeds(settings: Settings) -> tuple[LocalAccountSeed, ...]:
    if not settings.auth_enabled:
        return ()
    if settings.cleaning_access_code is None or settings.office_access_code is None:
        raise RuntimeError(
            "CLEANING_ACCESS_CODE and OFFICE_ACCESS_CODE are required when AUTH_ENABLED=true"
        )
    return (
        LocalAccountSeed(
            slug="cleaning-demo",
            display_name="Чистая территория",
            profile_slug="cleaning-moscow",
            access_code=settings.cleaning_access_code,
        ),
        LocalAccountSeed(
            slug="office-demo",
            display_name="Офисное снабжение",
            profile_slug="office-supply-moscow",
            access_code=settings.office_access_code,
        ),
    )


def create_raw_store(settings: Settings) -> RawStore:
    if settings.raw_store_backend == "memory":
        return MemoryRawStore()
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        region_name=settings.s3_region,
    )
    store = S3RawStore(client, bucket=settings.s3_bucket)
    store.ensure_bucket()
    return store


def create_gigachat_client(settings: Settings) -> GigaChatClient | None:
    if settings.gigachat_api_key is None:
        return None
    return GigaChatClient(
        authorization_key=settings.gigachat_api_key,
        scope=settings.gigachat_scope,
        ca_bundle_file=settings.gigachat_ca_bundle_file,
        model=settings.gigachat_model,
        oauth_url=settings.gigachat_oauth_url,
        api_base_url=settings.gigachat_api_base_url,
    )


def create_official_source_client(settings: Settings) -> OfficialSourceClient:
    return OfficialSourceClient(eis_ca_files=(settings.eis_root_ca_file, settings.eis_sub_ca_file))


Now = Callable[[], datetime]
