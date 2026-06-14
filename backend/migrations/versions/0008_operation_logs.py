"""add operation logs

Revision ID: 0008_operation_logs
Revises: 0007_import_jobs
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_operation_logs"
down_revision: str | None = "0007_import_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level", sa.String(length=20), nullable=False, server_default="info"),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_operation_logs_id", "operation_logs", ["id"])
    op.create_index("ix_operation_logs_module", "operation_logs", ["module"])


def downgrade() -> None:
    op.drop_index("ix_operation_logs_module", table_name="operation_logs")
    op.drop_index("ix_operation_logs_id", table_name="operation_logs")
    op.drop_table("operation_logs")
