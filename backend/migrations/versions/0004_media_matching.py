"""add media matching

Revision ID: 0004_media_matching
Revises: 0003_source_management
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_media_matching"
down_revision: str | None = "0003_source_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_item_id", sa.Integer(), sa.ForeignKey("source_items.id"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("original_title", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("episode_title", sa.Text(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_item_id", name="uq_media_matches_source_item_id"),
    )
    op.create_index("ix_media_matches_id", "media_matches", ["id"])
    op.create_index("ix_media_matches_source_item_id", "media_matches", ["source_item_id"])


def downgrade() -> None:
    op.drop_index("ix_media_matches_source_item_id", table_name="media_matches")
    op.drop_index("ix_media_matches_id", table_name="media_matches")
    op.drop_table("media_matches")
