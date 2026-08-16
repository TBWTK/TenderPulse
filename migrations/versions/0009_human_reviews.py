"""Add immutable human review revisions.

Revision ID: 0009_human_reviews
Revises: 0008_local_accounts
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_human_reviews"
down_revision: str | None = "0008_local_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("record_version_id", sa.Uuid(), nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["company_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["record_version_id"], ["procurement_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["supersedes_id"], ["human_reviews.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "profile_id", "record_version_id", "revision"),
        sa.UniqueConstraint("supersedes_id"),
    )
    op.create_index("ix_human_reviews_account_id", "human_reviews", ["account_id"])
    op.create_index("ix_human_reviews_profile_id", "human_reviews", ["profile_id"])
    op.create_index("ix_human_reviews_record_version_id", "human_reviews", ["record_version_id"])
    op.create_index("ix_human_reviews_label", "human_reviews", ["label"])
    op.create_index("ix_human_reviews_reason", "human_reviews", ["reason"])
    op.create_index("ix_human_reviews_created_at", "human_reviews", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_human_reviews_created_at", table_name="human_reviews")
    op.drop_index("ix_human_reviews_reason", table_name="human_reviews")
    op.drop_index("ix_human_reviews_label", table_name="human_reviews")
    op.drop_index("ix_human_reviews_record_version_id", table_name="human_reviews")
    op.drop_index("ix_human_reviews_profile_id", table_name="human_reviews")
    op.drop_index("ix_human_reviews_account_id", table_name="human_reviews")
    op.drop_table("human_reviews")
