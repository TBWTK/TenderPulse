from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import boto3  # type: ignore[import-untyped]
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from tenderpulse.ai.gigachat import GigaChatClient
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
