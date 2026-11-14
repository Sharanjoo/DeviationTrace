"""add org onboarding status (onboarded_at, scope_category)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("scope_category", sa.String(64), nullable=True))

    # Orgs that already adopted a scope template before this column existed
    # (they have org-specific checklist items) count as onboarded, so they
    # aren't sent back through onboarding. Their template isn't recorded
    # anywhere, so scope_category stays NULL for them.
    op.execute(
        """
        UPDATE organizations o
        SET onboarded_at = o.created_at
        WHERE EXISTS (SELECT 1 FROM audit_checklist_items i WHERE i.org_id = o.id)
        """
    )


def downgrade() -> None:
    op.drop_column("organizations", "scope_category")
    op.drop_column("organizations", "onboarded_at")
