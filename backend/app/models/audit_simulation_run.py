import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditSimulationRun(Base):
    """One execution of the internal audit simulation, kept forever as a
    history entry. AuditChecklistFinding holds only the *current* result per
    checklist item (upserted every run); this table plus its items is the
    immutable record of what each run found, which reports are built from.

    run_number counts up per org (1, 2, 3...) and is shown as SIM-0001."""

    __tablename__ = "audit_simulation_runs"
    __table_args__ = (UniqueConstraint("org_id", "run_number", name="uq_audit_simulation_run_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    missing: Mapped[int] = mapped_column(Integer, nullable=False)
    incomplete: Mapped[int] = mapped_column(Integer, nullable=False)
    satisfied: Mapped[int] = mapped_column(Integer, nullable=False)

    items: Mapped[list["AuditSimulationRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AuditSimulationRunItem.position"
    )

    @property
    def run_code(self) -> str:
        return f"SIM-{self.run_number:04d}"

    @property
    def total(self) -> int:
        return self.missing + self.incomplete + self.satisfied


class AuditSimulationRunItem(Base):
    """A frozen copy of one checklist result at the time of the run. Text is
    copied rather than linked, so later checklist edits, exclusions, or
    deleted documents never change what a past run (or its report) says."""

    __tablename__ = "audit_simulation_run_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audit_simulation_runs.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str] = mapped_column(String(32), nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    citation: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # missing | incomplete | satisfied
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # critical | major | resolved
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    matched_document_title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    run: Mapped[AuditSimulationRun] = relationship(back_populates="items")
