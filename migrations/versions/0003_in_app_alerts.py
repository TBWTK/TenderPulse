"""Idempotent in-app alert outbox.

Revision ID: 0003_in_app_alerts
Revises: 0002_ai_evidence
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_in_app_alerts"
down_revision: str | None = "0002_ai_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("record_version_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["company_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["record_version_id"], ["procurement_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in ("idempotency_key", "profile_id", "record_version_id", "channel", "status"):
        op.create_index(f"ix_alert_events_{column}", "alert_events", [column])


def downgrade() -> None:
    op.drop_table("alert_events")
