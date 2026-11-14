"""add user roles, names and active flag

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-14

Every existing user registered their own org (one user per org until now),
so all of them become that org's admin.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="member"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("UPDATE users SET role = 'admin'")


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
    op.drop_column("users", "full_name")
