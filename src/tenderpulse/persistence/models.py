from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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


class CompanyProfileRow(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (UniqueConstraint("slug", "version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


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
