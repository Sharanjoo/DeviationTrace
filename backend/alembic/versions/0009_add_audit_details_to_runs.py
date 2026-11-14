"""add audit details and draft status to audit simulation runs

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DETAIL_COLUMNS = [
    ("title", sa.String(255)),
    ("audit_type", sa.String(64)),
    ("planned_date", sa.Date()),
    ("lead_name", sa.String(255)),
    ("lead_employee_id", sa.String(64)),
    ("lead_title", sa.String(255)),
    ("lead_email", sa.String(255)),
    ("objective", sa.Text()),
    ("departments", postgresql.ARRAY(sa.String(32))),
    ("department_contacts", postgresql.JSONB()),
]


def upgrade() -> None:
    # Existing runs were all executed immediately, so they're "completed".
    op.add_column(
        "audit_simulation_runs",
        sa.Column("status", sa.String(16), nullable=False, server_default="completed"),
    )
    op.add_column("audit_simulation_runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE audit_simulation_runs SET completed_at = created_at")
    for name in ("missing", "incomplete", "satisfied"):
        op.alter_column("audit_simulation_runs", name, nullable=True)
    for name, type_ in _DETAIL_COLUMNS:
        op.add_column("audit_simulation_runs", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_DETAIL_COLUMNS):
        op.drop_column("audit_simulation_runs", name)
    op.execute("DELETE FROM audit_simulation_run_items WHERE run_id IN (SELECT id FROM audit_simulation_runs WHERE status = 'draft')")
    op.execute("DELETE FROM audit_simulation_runs WHERE status = 'draft'")
    for name in ("missing", "incomplete", "satisfied"):
        op.alter_column("audit_simulation_runs", name, nullable=False)
    op.drop_column("audit_simulation_runs", "completed_at")
    op.drop_column("audit_simulation_runs", "status")
