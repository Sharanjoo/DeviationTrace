"""add plain-English titles to regulatory clauses

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-14

Titles come from the clause YAML; re-run python -m app.seed.load_clauses to
fill them in.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("regulatory_clauses", sa.Column("title", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("regulatory_clauses", "title")
