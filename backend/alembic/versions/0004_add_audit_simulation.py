"""add audit simulation tables and document department

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("department", sa.String(32), nullable=True))
    op.create_index("ix_documents_department", "documents", ["department"])

    op.create_table(
        "audit_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("department", sa.String(32), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("citation", sa.String(128), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("match_phrases", postgresql.ARRAY(sa.String(255)), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("department", "item_name", "version", name="uq_checklist_item_identity"),
    )
    op.create_index("ix_audit_checklist_items_department", "audit_checklist_items", ["department"])

    op.create_table(
        "audit_checklist_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "checklist_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_checklist_items.id"),
            nullable=False,
        ),
        sa.Column("matched_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "checklist_item_id", name="uq_audit_finding_identity"),
    )
    op.create_index("ix_audit_checklist_findings_org_id", "audit_checklist_findings", ["org_id"])
    op.create_index("ix_audit_checklist_findings_severity", "audit_checklist_findings", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_audit_checklist_findings_severity", table_name="audit_checklist_findings")
    op.drop_index("ix_audit_checklist_findings_org_id", table_name="audit_checklist_findings")
    op.drop_table("audit_checklist_findings")

    op.drop_index("ix_audit_checklist_items_department", table_name="audit_checklist_items")
    op.drop_table("audit_checklist_items")

    op.drop_index("ix_documents_department", table_name="documents")
    op.drop_column("documents", "department")
