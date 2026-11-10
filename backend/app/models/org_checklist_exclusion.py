import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrgChecklistExclusion(Base):
    """An org opting out of one global (org_id IS NULL) AuditChecklistItem.
    Only meaningful for global items — a custom item an org created itself
    is simply deleted instead of excluded."""

    __tablename__ = "org_checklist_exclusions"
    __table_args__ = (UniqueConstraint("org_id", "checklist_item_id", name="uq_org_checklist_exclusion_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    checklist_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_checklist_items.id"), nullable=False
    )
    excluded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
