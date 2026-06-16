"""add metadata proxy settings

Revision ID: 0013_metadata_proxy_settings
Revises: 0012_nas115_provider
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_metadata_proxy_settings"
down_revision: str | None = "0012_nas115_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "metadata_proxy_type",
                sa.String(length=20),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(sa.Column("metadata_proxy_host", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("metadata_proxy_port", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("metadata_proxy_username", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column("metadata_proxy_password", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("metadata_proxy_password")
        batch_op.drop_column("metadata_proxy_username")
        batch_op.drop_column("metadata_proxy_port")
        batch_op.drop_column("metadata_proxy_host")
        batch_op.drop_column("metadata_proxy_type")
