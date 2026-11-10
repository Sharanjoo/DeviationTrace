"""add org checklist customization (per-org checklist items + exclusions)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # org_id nullable: NULL means "global library item" (today's behavior,
    # unchanged for every existing row), non-null means an org-specific
    # custom item that only applies to that org.
    op.add_column(
        "audit_checklist_items",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
    )
    op.create_index("ix_audit_checklist_items_org_id", "audit_checklist_items", ["org_id"])

    op.drop_constraint("uq_checklist_item_identity", "audit_checklist_items", type_="unique")
    op.create_unique_constraint(
        "uq_checklist_item_identity",
        "audit_checklist_items",
        ["org_id", "department", "item_name", "version"],
    )

    op.create_table(
        "org_checklist_exclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "checklist_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_checklist_items.id"),
            nullable=False,
        ),
        sa.Column("excluded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "checklist_item_id", name="uq_org_checklist_exclusion_identity"),
    )
    op.create_index("ix_org_checklist_exclusions_org_id", "org_checklist_exclusions", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_org_checklist_exclusions_org_id", table_name="org_checklist_exclusions")
    op.drop_table("org_checklist_exclusions")

    op.drop_constraint("uq_checklist_item_identity", "audit_checklist_items", type_="unique")
    op.create_unique_constraint(
        "uq_checklist_item_identity",
        "audit_checklist_items",
        ["department", "item_name", "version"],
    )

    op.drop_index("ix_audit_checklist_items_org_id", table_name="audit_checklist_items")
    op.drop_column("audit_checklist_items", "org_id")
