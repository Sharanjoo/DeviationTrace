"""add clause matching fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "regulatory_clauses",
        sa.Column(
            "match_phrases",
            postgresql.ARRAY(sa.String(255)),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column("regulatory_clauses", sa.Column("expected_heading", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("regulatory_clauses", "expected_heading")
    op.drop_column("regulatory_clauses", "match_phrases")
