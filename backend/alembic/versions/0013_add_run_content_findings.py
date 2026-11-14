"""add content findings to audit simulation runs

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-14

The SOP / deviation content check moves inside the internal audit
simulation: each run stores the content gaps found in its departments' SOPs
and deviation reports, with a review decision per gap.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_simulation_runs", sa.Column("content_documents_checked", sa.Integer(), nullable=True))
    op.create_table(
        "audit_simulation_content_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_simulation_runs.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(32), nullable=False),
        sa.Column("document_title", sa.String(512), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("regulation", sa.String(32), nullable=False),
        sa.Column("clause_number", sa.String(64), nullable=False),
        sa.Column("requirement_title", sa.String(255), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("section_heading", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_audit_simulation_content_findings_run_id", "audit_simulation_content_findings", ["run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_simulation_content_findings_run_id", table_name="audit_simulation_content_findings")
    op.drop_table("audit_simulation_content_findings")
    op.drop_column("audit_simulation_runs", "content_documents_checked")
