"""add app settings

Revision ID: 0002_app_settings
Revises: 0001_initial_schema
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_app_settings"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_api_key", sa.String(length=255), nullable=True),
        sa.Column("tmdb_language", sa.String(length=20), nullable=False, server_default="zh-CN"),
        sa.Column("tmdb_region", sa.String(length=20), nullable=False, server_default="CN"),
        sa.Column("qbittorrent_url", sa.Text(), nullable=True),
        sa.Column("qbittorrent_username", sa.String(length=255), nullable=True),
        sa.Column("qbittorrent_password", sa.String(length=255), nullable=True),
        sa.Column("download_dir", sa.Text(), nullable=False, server_default="/downloads"),
        sa.Column("media_library_dir", sa.Text(), nullable=False, server_default="/media"),
        sa.Column("matching_threshold", sa.Integer(), nullable=False, server_default="85"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
