"""add source management

Revision ID: 0003_source_management
Revises: 0002_app_settings
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_source_management"
down_revision: str | None = "0002_app_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_sites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="webpage"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auth_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("fetch_interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("hash_pattern", sa.Text(), nullable=False, server_default=""),
        sa.Column("title_cleanup_rules", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_source_sites_id", "source_sites", ["id"])
    op.create_table(
        "source_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("source_sites.id"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("info_hash", sa.String(length=40), nullable=False),
        sa.Column("magnet_uri", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("info_hash", name="uq_source_items_info_hash"),
    )
    op.create_index("ix_source_items_id", "source_items", ["id"])
    op.create_index("ix_source_items_info_hash", "source_items", ["info_hash"])
    op.create_index("ix_source_items_source_id", "source_items", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_source_items_source_id", table_name="source_items")
    op.drop_index("ix_source_items_info_hash", table_name="source_items")
    op.drop_index("ix_source_items_id", table_name="source_items")
    op.drop_table("source_items")
    op.drop_index("ix_source_sites_id", table_name="source_sites")
    op.drop_table("source_sites")
