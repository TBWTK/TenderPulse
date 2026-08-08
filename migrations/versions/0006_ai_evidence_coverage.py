"""Backfill explicit coverage status in legacy AI evidence payloads.

Revision ID: 0006_ai_evidence_coverage
Revises: 0005_webhook_alert_delivery
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0006_ai_evidence_coverage"
down_revision: str | None = "0005_webhook_alert_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ATTEMPTS = sa.table(
    "ai_extraction_attempts",
    sa.column("id", sa.Uuid()),
    sa.column("payload", sa.JSON()),
)


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(_ATTEMPTS.c.id, _ATTEMPTS.c.payload).where(_ATTEMPTS.c.payload.is_not(None))
    ).mappings()
    for row in rows:
        payload: dict[str, Any] = dict(row["payload"])
        changed = False
        for category in ("requirements", "deadlines"):
            status_field = f"{category}_status"
            if status_field not in payload:
                payload[status_field] = "found" if payload.get(category) else "unknown"
                changed = True
        if changed:
            connection.execute(
                sa.update(_ATTEMPTS).where(_ATTEMPTS.c.id == row["id"]).values(payload=payload)
            )


def downgrade() -> None:
    # Coverage fields are additive evidence; removing them would recreate ambiguity.
    pass
