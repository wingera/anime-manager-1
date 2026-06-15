"""add auto rename rules and actions

Revision ID: 0011_auto_rename
Revises: 0010_tmdb_include_adult
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_auto_rename"
down_revision: str | None = "0010_tmdb_include_adult"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("rename_previews") as batch_op:
        batch_op.add_column(sa.Column("task_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("file_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("parent_id", sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column("original_name", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(sa.Column("target_name", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("file_type", sa.String(length=40), nullable=False, server_default="other")
        )
        batch_op.add_column(sa.Column("episode_number", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("confidence", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("status", sa.String(length=40), nullable=False, server_default="pending")
        )
        batch_op.create_index("ix_rename_previews_task_id", ["task_id"])

    op.create_table(
        "rename_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("auto_execute", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "name_template",
            sa.Text(),
            nullable=False,
            server_default="{clean_title} - {episode}{ext}",
        ),
        sa.Column("episode_padding", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("remove_words", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rename_rules_id", "rename_rules", ["id"])
    op.create_table(
        "rename_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("preview_id", sa.Integer(), sa.ForeignKey("rename_previews.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("download_tasks.id"), nullable=False),
        sa.Column("file_id", sa.String(length=120), nullable=False),
        sa.Column("old_name", sa.Text(), nullable=False),
        sa.Column("new_name", sa.Text(), nullable=False),
        sa.Column("old_parent_id", sa.String(length=120), nullable=True),
        sa.Column("new_parent_id", sa.String(length=120), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False, server_default="rename"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="completed"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rename_actions_id", "rename_actions", ["id"])
    op.create_index("ix_rename_actions_preview_id", "rename_actions", ["preview_id"])
    op.create_index("ix_rename_actions_task_id", "rename_actions", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_rename_actions_task_id", table_name="rename_actions")
    op.drop_index("ix_rename_actions_preview_id", table_name="rename_actions")
    op.drop_index("ix_rename_actions_id", table_name="rename_actions")
    op.drop_table("rename_actions")
    op.drop_index("ix_rename_rules_id", table_name="rename_rules")
    op.drop_table("rename_rules")
    with op.batch_alter_table("rename_previews") as batch_op:
        batch_op.drop_index("ix_rename_previews_task_id")
        batch_op.drop_column("status")
        batch_op.drop_column("confidence")
        batch_op.drop_column("episode_number")
        batch_op.drop_column("file_type")
        batch_op.drop_column("file_size")
        batch_op.drop_column("target_name")
        batch_op.drop_column("original_name")
        batch_op.drop_column("parent_id")
        batch_op.drop_column("file_id")
        batch_op.drop_column("task_id")
