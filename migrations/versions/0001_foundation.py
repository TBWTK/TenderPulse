"""Foundation lineage, canonical history and profiles.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_parameters", sa.JSON(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_source", "ingestion_runs", ["source"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_raw_sha256", "ingestion_runs", ["raw_sha256"])

    op.create_table(
        "raw_artifacts",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("object_uri", sa.String(length=2048), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sha256"),
        sa.UniqueConstraint("object_uri"),
    )
    op.create_index("ix_raw_artifacts_source", "raw_artifacts", ["source"])

    op.create_table(
        "procurement_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_record_id", sa.String(length=512), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "source_record_id"),
    )
    op.create_index("ix_procurement_records_source", "procurement_records", ["source"])
    op.create_index(
        "ix_procurement_records_source_record_id",
        "procurement_records",
        ["source_record_id"],
    )
    op.create_index("ix_procurement_records_kind", "procurement_records", ["kind"])

    op.create_table(
        "procurement_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("canonical_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["record_id"], ["procurement_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", "version"),
    )
    op.create_index("ix_procurement_versions_record_id", "procurement_versions", ["record_id"])
    op.create_index(
        "ix_procurement_versions_canonical_fingerprint",
        "procurement_versions",
        ["canonical_fingerprint"],
    )
    op.create_index("ix_procurement_versions_raw_sha256", "procurement_versions", ["raw_sha256"])
    op.create_index(
        "ix_procurement_versions_ingestion_run_id",
        "procurement_versions",
        ["ingestion_run_id"],
    )
    op.create_index("ix_procurement_versions_valid_to", "procurement_versions", ["valid_to"])
    op.create_index(
        "uq_procurement_versions_one_current",
        "procurement_versions",
        ["record_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
        sqlite_where=sa.text("valid_to IS NULL"),
    )

    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "version"),
    )
    op.create_index("ix_company_profiles_slug", "company_profiles", ["slug"])
    op.create_index("ix_company_profiles_active", "company_profiles", ["active"])


def downgrade() -> None:
    op.drop_table("company_profiles")
    op.drop_table("procurement_versions")
    op.drop_table("procurement_records")
    op.drop_table("raw_artifacts")
    op.drop_table("ingestion_runs")
