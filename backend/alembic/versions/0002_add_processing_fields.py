"""add processing fields to documents

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("detected_process_area", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "detected_process_area")
    op.drop_column("documents", "processing_error")
