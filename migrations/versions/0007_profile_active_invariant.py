"""Enforce one active profile version per company slug.

Revision ID: 0007_profile_active_invariant
Revises: 0006_ai_evidence_coverage
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_profile_active_invariant"
down_revision: str | None = "0006_ai_evidence_coverage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_company_profiles_one_active",
        "company_profiles",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE"),
        sqlite_where=sa.text("active = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_company_profiles_one_active", table_name="company_profiles")
