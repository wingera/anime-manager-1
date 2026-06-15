"""add tmdb adult search option

Revision ID: 0010_tmdb_include_adult
Revises: 0009_source_detail_scan
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_tmdb_include_adult"
down_revision: str | None = "0009_source_detail_scan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column(
            "tmdb_include_adult",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "tmdb_include_adult")
