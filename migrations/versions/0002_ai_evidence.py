"""Traceable AI extraction attempts.

Revision ID: 0002_ai_evidence
Revises: 0001_foundation
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_ai_evidence"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_extraction_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_version_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("requested_model", sa.String(length=128), nullable=False),
        sa.Column("response_model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("output_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_version_id"], ["procurement_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_extraction_attempts_record_version_id",
        "ai_extraction_attempts",
        ["record_version_id"],
    )
    op.create_index("ix_ai_extraction_attempts_provider", "ai_extraction_attempts", ["provider"])
    op.create_index(
        "ix_ai_extraction_attempts_input_sha256", "ai_extraction_attempts", ["input_sha256"]
    )
    op.create_index(
        "ix_ai_extraction_attempts_raw_sha256", "ai_extraction_attempts", ["raw_sha256"]
    )
    op.create_index("ix_ai_extraction_attempts_status", "ai_extraction_attempts", ["status"])
    op.create_index(
        "uq_ai_extraction_validated_cache",
        "ai_extraction_attempts",
        ["record_version_id", "provider", "requested_model", "prompt_version", "input_sha256"],
        unique=True,
        postgresql_where=sa.text("status = 'validated'"),
        sqlite_where=sa.text("status = 'validated'"),
    )


def downgrade() -> None:
    op.drop_table("ai_extraction_attempts")
