"""add nas115 provider settings

Revision ID: 0012_nas115_provider
Revises: 0011_auto_rename
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_nas115_provider"
down_revision: str | None = "0011_auto_rename"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "download_provider",
                sa.String(length=40),
                nullable=False,
                server_default="qbittorrent",
            )
        )
        batch_op.add_column(
            sa.Column("cloud115_enabled", sa.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "cloud115_service_url",
                sa.Text(),
                nullable=False,
                server_default="http://192.168.1.19:9527",
            )
        )
        batch_op.add_column(sa.Column("cloud115_service_token", sa.Text(), nullable=True))

    with op.batch_alter_table("download_tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "provider",
                sa.String(length=40),
                nullable=False,
                server_default="qbittorrent",
            )
        )
        batch_op.add_column(sa.Column("provider_task_id", sa.String(length=120), nullable=True))

    with op.batch_alter_table("download_files") as batch_op:
        batch_op.add_column(sa.Column("provider_file_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("parent_id", sa.String(length=120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("download_files") as batch_op:
        batch_op.drop_column("parent_id")
        batch_op.drop_column("provider_file_id")
    with op.batch_alter_table("download_tasks") as batch_op:
        batch_op.drop_column("provider_task_id")
        batch_op.drop_column("provider")
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("cloud115_service_token")
        batch_op.drop_column("cloud115_service_url")
        batch_op.drop_column("cloud115_enabled")
        batch_op.drop_column("download_provider")
