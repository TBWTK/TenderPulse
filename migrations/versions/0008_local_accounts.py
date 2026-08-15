"""Add local accounts, access credentials and revocable web sessions.

Revision ID: 0008_local_accounts
Revises: 0007_profile_active_invariant
Create Date: 2026-08-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_local_accounts"
down_revision: str | None = "0007_profile_active_invariant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("profile_slug", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_accounts_slug", "accounts", ["slug"])
    op.create_index("ix_accounts_role", "accounts", ["role"])
    op.create_index("ix_accounts_profile_slug", "accounts", ["profile_slug"])
    op.create_index("ix_accounts_active", "accounts", ["active"])

    op.create_table(
        "access_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("code_prefix", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_access_credentials_account_id", "access_credentials", ["account_id"])
    op.create_index("ix_access_credentials_code_hash", "access_credentials", ["code_hash"])
    op.create_index("ix_access_credentials_active", "access_credentials", ["active"])

    op.create_table(
        "web_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_web_sessions_account_id", "web_sessions", ["account_id"])
    op.create_index("ix_web_sessions_token_hash", "web_sessions", ["token_hash"])
    op.create_index("ix_web_sessions_expires_at", "web_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_web_sessions_expires_at", table_name="web_sessions")
    op.drop_index("ix_web_sessions_token_hash", table_name="web_sessions")
    op.drop_index("ix_web_sessions_account_id", table_name="web_sessions")
    op.drop_table("web_sessions")
    op.drop_index("ix_access_credentials_active", table_name="access_credentials")
    op.drop_index("ix_access_credentials_code_hash", table_name="access_credentials")
    op.drop_index("ix_access_credentials_account_id", table_name="access_credentials")
    op.drop_table("access_credentials")
    op.drop_index("ix_accounts_active", table_name="accounts")
    op.drop_index("ix_accounts_profile_slug", table_name="accounts")
    op.drop_index("ix_accounts_role", table_name="accounts")
    op.drop_index("ix_accounts_slug", table_name="accounts")
    op.drop_table("accounts")
