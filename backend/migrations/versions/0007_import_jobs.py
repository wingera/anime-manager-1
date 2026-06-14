"""add import jobs and file actions

Revision ID: 0007_import_jobs
Revises: 0006_file_analysis_preview
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_import_jobs"
down_revision: str | None = "0006_file_analysis_preview"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "download_task_id",
            sa.Integer(),
            sa.ForeignKey("download_tasks.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("mode", sa.String(length=40), nullable=False, server_default="hardlink"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_import_jobs_id", "import_jobs", ["id"])
    op.create_index("ix_import_jobs_download_task_id", "import_jobs", ["download_task_id"])
    op.create_table(
        "import_file_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_job_id", sa.Integer(), sa.ForeignKey("import_jobs.id"), nullable=False),
        sa.Column(
            "download_file_id",
            sa.Integer(),
            sa.ForeignKey("download_files.id"),
            nullable=False,
        ),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("action_type", sa.String(length=40), nullable=False, server_default="hardlink"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_import_file_actions_id", "import_file_actions", ["id"])
    op.create_index(
        "ix_import_file_actions_import_job_id",
        "import_file_actions",
        ["import_job_id"],
    )
    op.create_index(
        "ix_import_file_actions_download_file_id",
        "import_file_actions",
        ["download_file_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_import_file_actions_download_file_id", table_name="import_file_actions")
    op.drop_index("ix_import_file_actions_import_job_id", table_name="import_file_actions")
    op.drop_index("ix_import_file_actions_id", table_name="import_file_actions")
    op.drop_table("import_file_actions")
    op.drop_index("ix_import_jobs_download_task_id", table_name="import_jobs")
    op.drop_index("ix_import_jobs_id", table_name="import_jobs")
    op.drop_table("import_jobs")
