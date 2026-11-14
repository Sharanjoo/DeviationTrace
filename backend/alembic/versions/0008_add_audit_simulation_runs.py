"""add audit simulation run history (runs + frozen run items)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("missing", sa.Integer(), nullable=False),
        sa.Column("incomplete", sa.Integer(), nullable=False),
        sa.Column("satisfied", sa.Integer(), nullable=False),
        sa.UniqueConstraint("org_id", "run_number", name="uq_audit_simulation_run_number"),
    )
    op.create_index("ix_audit_simulation_runs_org_id", "audit_simulation_runs", ["org_id"])

    op.create_table(
        "audit_simulation_run_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_simulation_runs.id"), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(32), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("citation", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("matched_document_title", sa.String(512), nullable=True),
    )
    op.create_index("ix_audit_simulation_run_items_run_id", "audit_simulation_run_items", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_simulation_run_items_run_id", table_name="audit_simulation_run_items")
    op.drop_table("audit_simulation_run_items")
    op.drop_index("ix_audit_simulation_runs_org_id", table_name="audit_simulation_runs")
    op.drop_table("audit_simulation_runs")
