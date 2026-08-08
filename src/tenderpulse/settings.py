from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./tenderpulse.db"
    raw_store_backend: Literal["memory", "s3"] = "memory"
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: SecretStr = SecretStr("tenderpulse-local")
    s3_secret_key: SecretStr = SecretStr("tenderpulse-local-only")
    s3_bucket: str = "tenderpulse-raw"
    s3_region: str = "us-east-1"

    gigachat_api_key: SecretStr | None = None
    gigachat_client_id: SecretStr | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_ca_bundle_file: Path = Path("certs/russian_trusted_root_ca_pem.crt")
    gigachat_model: str = "GigaChat-2"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_api_base_url: str = "https://api.giga.chat/v1"

    live_ingestion_enabled: bool = False
    ingestion_interval_seconds: int = Field(default=3600, ge=60)
    source_record_limit: int = Field(default=100, ge=1, le=500)
    ted_lookback_days: int = Field(default=14, ge=1, le=90)
    usa_lookback_days: int = Field(default=365, ge=1, le=731)
