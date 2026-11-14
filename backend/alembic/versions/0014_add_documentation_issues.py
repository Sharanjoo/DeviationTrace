"""add documentation completeness issues

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-14

Per-document issues (blank signatures, stamps, dates, entries, unfilled
placeholders), plus each internal audit run's frozen copy of them.
Existing documents are checked the first time they're used.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _issue_columns():
    return [
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=False, server_default="high"),
    ]


def upgrade() -> None:
    op.add_column("documents", sa.Column("documentation_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "documentation_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        *_issue_columns(),
    )
    op.create_index("ix_documentation_issues_document_id", "documentation_issues", ["document_id"])

    op.create_table(
        "audit_simulation_documentation_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_simulation_runs.id"), nullable=False),
        sa.Column("department", sa.String(32), nullable=False),
        sa.Column("document_title", sa.String(512), nullable=False),
        *_issue_columns(),
    )
    op.create_index(
        "ix_audit_simulation_documentation_issues_run_id", "audit_simulation_documentation_issues", ["run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_simulation_documentation_issues_run_id", table_name="audit_simulation_documentation_issues")
    op.drop_table("audit_simulation_documentation_issues")
    op.drop_index("ix_documentation_issues_document_id", table_name="documentation_issues")
    op.drop_table("documentation_issues")
    op.drop_column("documents", "documentation_checked_at")
