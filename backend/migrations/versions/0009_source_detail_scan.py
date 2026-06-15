"""add source detail scan option

Revision ID: 0009_source_detail_scan
Revises: 0008_operation_logs
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_source_detail_scan"
down_revision: str | None = "0008_operation_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_sites",
        sa.Column(
            "scan_detail_pages",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("source_sites", "scan_detail_pages")
