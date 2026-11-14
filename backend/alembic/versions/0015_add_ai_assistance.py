"""add optional AI assistance: org settings, interaction log, assessments

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("audit_simulation_runs", sa.Column("content_documents", postgresql.JSONB(), nullable=True))

    op.create_table(
        "org_ai_settings",
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("provider", sa.String(32), nullable=False, server_default="anthropic"),
        sa.Column("model", sa.String(128), nullable=False, server_default="claude-opus-5-5"),
        sa.Column("region", sa.String(64), nullable=True),
        sa.Column("project_id", sa.String(128), nullable=True),
        sa.Column("resource", sa.String(128), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("redact_identifiers", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(255), nullable=True),
    )

    op.create_table(
        "ai_interactions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("run_id", UUID, sa.ForeignKey("audit_simulation_runs.id"), nullable=True),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("document_title", sa.String(512), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model_requested", sa.String(128), nullable=False),
        sa.Column("model_used", sa.String(128), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sections_sent", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("redacted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("redaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_ai_interactions_org_id", "ai_interactions", ["org_id"])
    op.create_index("ix_ai_interactions_run_id", "ai_interactions", ["run_id"])

    op.create_table(
        "audit_simulation_ai_assessments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("run_id", UUID, sa.ForeignKey("audit_simulation_runs.id"), nullable=False),
        sa.Column("interaction_id", UUID, sa.ForeignKey("ai_interactions.id"), nullable=False),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("document_title", sa.String(512), nullable=False),
        sa.Column("citation", sa.String(128), nullable=False),
        sa.Column("requirement_title", sa.String(255), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("evidence_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_simulation_ai_assessments_run_id", "audit_simulation_ai_assessments", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_simulation_ai_assessments_run_id", table_name="audit_simulation_ai_assessments")
    op.drop_table("audit_simulation_ai_assessments")
    op.drop_index("ix_ai_interactions_run_id", table_name="ai_interactions")
    op.drop_index("ix_ai_interactions_org_id", table_name="ai_interactions")
    op.drop_table("ai_interactions")
    op.drop_table("org_ai_settings")
    op.drop_column("audit_simulation_runs", "content_documents")
