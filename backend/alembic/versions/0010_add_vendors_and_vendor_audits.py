"""add vendors and vendor audits

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-14

Existing vendor_audit_report documents are left unlinked; the app lists them
as "unassigned reports" for the user to attach to the right vendor, rather
than guessing a vendor name from the filename.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("vendor_category", sa.String(32), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "name", name="uq_vendor_name_per_org"),
    )
    op.create_index("ix_vendors_org_id", "vendors", ["org_id"])

    op.create_table(
        "vendor_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("audit_number", sa.Integer(), nullable=False),
        sa.Column("audit_date", sa.Date(), nullable=True),
        sa.Column("auditor_name", sa.String(255), nullable=True),
        sa.Column("auditor_employee_id", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("org_id", "audit_number", name="uq_vendor_audit_number"),
        sa.UniqueConstraint("document_id", name="uq_vendor_audit_document"),
    )
    op.create_index("ix_vendor_audits_org_id", "vendor_audits", ["org_id"])
    op.create_index("ix_vendor_audits_vendor_id", "vendor_audits", ["vendor_id"])


def downgrade() -> None:
    op.drop_index("ix_vendor_audits_vendor_id", table_name="vendor_audits")
    op.drop_index("ix_vendor_audits_org_id", table_name="vendor_audits")
    op.drop_table("vendor_audits")
    op.drop_index("ix_vendors_org_id", table_name="vendors")
    op.drop_table("vendors")
