"""add file analysis and rename preview

Revision ID: 0006_file_analysis_preview
Revises: 0005_download_tasks
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_file_analysis_preview"
down_revision: str | None = "0005_download_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "download_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "download_task_id",
            sa.Integer(),
            sa.ForeignKey("download_tasks.id"),
            nullable=False,
        ),
        sa.Column("file_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("file_type", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("analysis_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "download_task_id",
            "file_index",
            name="uq_download_files_task_index",
        ),
    )
    op.create_index("ix_download_files_id", "download_files", ["id"])
    op.create_index("ix_download_files_download_task_id", "download_files", ["download_task_id"])
    op.create_table(
        "rename_previews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "download_file_id",
            sa.Integer(),
            sa.ForeignKey("download_files.id"),
            nullable=False,
        ),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("conflict", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("warning_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("download_file_id", name="uq_rename_previews_download_file_id"),
    )
    op.create_index("ix_rename_previews_id", "rename_previews", ["id"])
    op.create_index("ix_rename_previews_download_file_id", "rename_previews", ["download_file_id"])


def downgrade() -> None:
    op.drop_index("ix_rename_previews_download_file_id", table_name="rename_previews")
    op.drop_index("ix_rename_previews_id", table_name="rename_previews")
    op.drop_table("rename_previews")
    op.drop_index("ix_download_files_download_task_id", table_name="download_files")
    op.drop_index("ix_download_files_id", table_name="download_files")
    op.drop_table("download_files")
