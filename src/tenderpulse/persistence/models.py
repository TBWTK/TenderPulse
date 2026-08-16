from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class IngestionRunRow(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RawArtifactRow(Base):
    __tablename__ = "raw_artifacts"

    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    object_uri: Mapped[str] = mapped_column(String(2048), unique=True)
    byte_size: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProcurementRecordRow(Base):
    __tablename__ = "procurement_records"
    __table_args__ = (UniqueConstraint("source", "source_record_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(32), index=True)
    source_record_id: Mapped[str] = mapped_column(String(512), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    current_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    versions: Mapped[list[ProcurementVersionRow]] = relationship(
        back_populates="procurement_record",
        cascade="all, delete-orphan",
    )


class ProcurementVersionRow(Base):
    __tablename__ = "procurement_versions"
    __table_args__ = (UniqueConstraint("record_id", "version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    record_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_records.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer)
    canonical_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    raw_sha256: Mapped[str] = mapped_column(String(64), index=True)
    ingestion_run_id: Mapped[UUID] = mapped_column(index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    procurement_record: Mapped[ProcurementRecordRow] = relationship(back_populates="versions")


class OrganizationRow(Base):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("source", "normalized_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(32), index=True)
    canonical_name: Mapped[str] = mapped_column(String(1024))
    normalized_name: Mapped[str] = mapped_column(String(1024), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OrganizationAliasRow(Base):
    __tablename__ = "organization_aliases"
    __table_args__ = (UniqueConstraint("organization_id", "alias_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    alias_name: Mapped[str] = mapped_column(String(1024))
    normalized_alias: Mapped[str] = mapped_column(String(1024), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProcurementOrganizationLinkRow(Base):
    __tablename__ = "procurement_organization_links"
    __table_args__ = (UniqueConstraint("record_version_id", "role", "ordinal"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    record_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_versions.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    alias_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_aliases.id", ondelete="RESTRICT"), index=True
    )
    role: Mapped[str] = mapped_column(String(32), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    source_name: Mapped[str] = mapped_column(String(1024))
    raw_sha256: Mapped[str] = mapped_column(String(64), index=True)


class CompanyProfileRow(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (
        UniqueConstraint("slug", "version"),
        Index(
            "uq_company_profiles_one_active",
            "slug",
            unique=True,
            postgresql_where=text("active IS TRUE"),
            sqlite_where=text("active = 1"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class AccountRow(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    profile_slug: Mapped[str] = mapped_column(String(128), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AccessCredentialRow(Base):
    __tablename__ = "access_credentials"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, index=True
    )
    code_prefix: Mapped[str] = mapped_column(String(32))
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebSessionRow(Base):
    __tablename__ = "web_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HumanReviewRow(Base):
    __tablename__ = "human_reviews"
    __table_args__ = (
        UniqueConstraint("account_id", "profile_id", "record_version_id", "revision"),
        UniqueConstraint("supersedes_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("company_profiles.id", ondelete="RESTRICT"), index=True
    )
    record_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_versions.id", ondelete="RESTRICT"), index=True
    )
    supersedes_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("human_reviews.id", ondelete="RESTRICT"), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AIExtractionAttemptRow(Base):
    __tablename__ = "ai_extraction_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    record_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_versions.id", ondelete="CASCADE"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), index=True)
    requested_model: Mapped[str] = mapped_column(String(128))
    response_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(128))
    input_sha256: Mapped[str] = mapped_column(String(64), index=True)
    output_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AlertEventRow(Base):
    __tablename__ = "alert_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("company_profiles.id", ondelete="CASCADE"), index=True
    )
    record_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_versions.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(32), index=True)
    policy_version: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertDeliveryAttemptRow(Base):
    __tablename__ = "alert_delivery_attempts"
    __table_args__ = (
        UniqueConstraint("alert_event_id", "channel", "destination_sha256", "attempt_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    alert_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("alert_events.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(32), index=True)
    destination_sha256: Mapped[str] = mapped_column(String(64), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
