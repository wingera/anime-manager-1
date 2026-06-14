"""add source item download tasks

Revision ID: 0005_download_tasks
Revises: 0004_media_matching
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_download_tasks"
down_revision: str | None = "0004_media_matching"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_download_tasks_resource_id", table_name="download_tasks")
    op.drop_table("download_tasks")
    op.create_table(
        "download_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_item_id", sa.Integer(), sa.ForeignKey("source_items.id"), nullable=False),
        sa.Column("qbittorrent_hash", sa.String(length=64), nullable=True),
        sa.Column("magnet_uri", sa.Text(), nullable=False),
        sa.Column("save_path", sa.Text(), nullable=False, server_default="/downloads"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_item_id", name="uq_download_tasks_source_item_id"),
    )
    op.create_index("ix_download_tasks_id", "download_tasks", ["id"])
    op.create_index("ix_download_tasks_source_item_id", "download_tasks", ["source_item_id"])


def downgrade() -> None:
    op.drop_index("ix_download_tasks_source_item_id", table_name="download_tasks")
    op.drop_index("ix_download_tasks_id", table_name="download_tasks")
    op.drop_table("download_tasks")
    op.create_table(
        "download_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("torrent_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("save_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default="pending_download",
        ),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_download_tasks_resource_id", "download_tasks", ["resource_id"])
