"""Audited opt-in webhook alert delivery attempts.

Revision ID: 0005_webhook_alert_delivery
Revises: 0004_organization_identity
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_webhook_alert_delivery"
down_revision: str | None = "0004_organization_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alert_delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_event_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("destination_sha256", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alert_event_id"], ["alert_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_event_id", "channel", "destination_sha256", "attempt_number"),
    )
    for column in (
        "alert_event_id",
        "channel",
        "destination_sha256",
        "idempotency_key",
        "status",
    ):
        op.create_index(
            f"ix_alert_delivery_attempts_{column}",
            "alert_delivery_attempts",
            [column],
        )


def downgrade() -> None:
    op.drop_table("alert_delivery_attempts")
