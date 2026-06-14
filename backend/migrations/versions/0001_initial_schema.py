"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authorization_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("fetch_interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("hash_pattern", sa.Text(), nullable=False, server_default=""),
        sa.Column("title_cleanup_rule", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("resource_hash", sa.String(length=40), nullable=False),
        sa.Column("magnet_uri", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending_review"),
        sa.Column("safety_status", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("resource_hash", name="uq_resources_resource_hash"),
    )
    op.create_index("ix_resources_resource_hash", "resources", ["resource_hash"])
    op.create_table(
        "metadata_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("original_title", sa.Text(), nullable=False, server_default=""),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_metadata_matches_resource_id", "metadata_matches", ["resource_id"])
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
    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("download_task_id", sa.Integer(), nullable=False),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("file_type", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("action", sa.String(length=40), nullable=False, server_default="pending_review"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_media_files_download_task_id", "media_files", ["download_task_id"])


def downgrade() -> None:
    op.drop_index("ix_media_files_download_task_id", table_name="media_files")
    op.drop_table("media_files")
    op.drop_index("ix_download_tasks_resource_id", table_name="download_tasks")
    op.drop_table("download_tasks")
    op.drop_index("ix_metadata_matches_resource_id", table_name="metadata_matches")
    op.drop_table("metadata_matches")
    op.drop_index("ix_resources_resource_hash", table_name="resources")
    op.drop_table("resources")
    op.drop_table("sources")
