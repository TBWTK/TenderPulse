"""Source-scoped buyer and supplier identity projection.

Revision ID: 0004_organization_identity
Revises: 0003_in_app_alerts
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_organization_identity"
down_revision: str | None = "0003_in_app_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("canonical_name", sa.String(length=1024), nullable=False),
        sa.Column("normalized_name", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "normalized_name"),
    )
    op.create_index("ix_organizations_source", "organizations", ["source"])
    op.create_index("ix_organizations_normalized_name", "organizations", ["normalized_name"])
    op.create_table(
        "organization_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("alias_name", sa.String(length=1024), nullable=False),
        sa.Column("normalized_alias", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "alias_name"),
    )
    op.create_index(
        "ix_organization_aliases_organization_id",
        "organization_aliases",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_aliases_normalized_alias",
        "organization_aliases",
        ["normalized_alias"],
    )
    op.create_table(
        "procurement_organization_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_version_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("alias_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=1024), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_version_id"], ["procurement_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["alias_id"], ["organization_aliases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_version_id", "role", "ordinal"),
    )
    for column in ("record_version_id", "organization_id", "alias_id", "role", "raw_sha256"):
        op.create_index(
            f"ix_procurement_organization_links_{column}",
            "procurement_organization_links",
            [column],
        )


def downgrade() -> None:
    op.drop_table("procurement_organization_links")
    op.drop_table("organization_aliases")
    op.drop_table("organizations")
