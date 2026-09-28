"""add vendor audit cross-check tables and document vendor_category

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("vendor_category", sa.String(32), nullable=True))
    op.create_index("ix_documents_vendor_category", "documents", ["vendor_category"])

    op.create_table(
        "vendor_standards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vendor_category", sa.String(32), nullable=False),
        sa.Column("requirement_name", sa.String(255), nullable=False),
        sa.Column("citation", sa.String(128), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("match_phrases", postgresql.ARRAY(sa.String(255)), nullable=False, server_default="{}"),
        sa.Column("expected_heading", sa.String(64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("vendor_category", "requirement_name", "version", name="uq_vendor_standard_identity"),
    )
    op.create_index("ix_vendor_standards_vendor_category", "vendor_standards", ["vendor_category"])

    op.create_table(
        "vendor_audit_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column(
            "section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_sections.id"), nullable=False
        ),
        sa.Column(
            "standard_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendor_standards.id"), nullable=False
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "standard_id", name="uq_vendor_audit_finding_identity"),
    )
    op.create_index("ix_vendor_audit_findings_document_id", "vendor_audit_findings", ["document_id"])
    op.create_index("ix_vendor_audit_findings_severity", "vendor_audit_findings", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_vendor_audit_findings_severity", table_name="vendor_audit_findings")
    op.drop_index("ix_vendor_audit_findings_document_id", table_name="vendor_audit_findings")
    op.drop_table("vendor_audit_findings")

    op.drop_index("ix_vendor_standards_vendor_category", table_name="vendor_standards")
    op.drop_table("vendor_standards")

    op.drop_index("ix_documents_vendor_category", table_name="documents")
    op.drop_column("documents", "vendor_category")
