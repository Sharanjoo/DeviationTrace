import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditSimulationRun(Base):
    """One execution of the internal audit simulation, kept forever as a
    history entry. AuditChecklistFinding holds only the *current* result per
    checklist item (upserted every run); this table plus its items is the
    immutable record of what each run found, which reports are built from.

    run_number counts up per org (1, 2, 3...) and is shown as SIM-0001.

    A run starts as a "draft" holding the audit's details (what audit, who
    leads it, which departments) while documents are uploaded, then becomes
    "completed" when executed. Draft runs have no counts or items yet. The
    number is assigned at draft creation so the ID is known from the start."""

    __tablename__ = "audit_simulation_runs"
    __table_args__ = (UniqueConstraint("org_id", "run_number", name="uq_audit_simulation_run_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")  # draft | completed
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    missing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incomplete: Mapped[int | None] = mapped_column(Integer, nullable=True)
    satisfied: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Audit details, entered before documents are uploaded. NULL for runs
    # started without them (quick runs via POST /audit-simulation/run).
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audit_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lead_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_employee_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Departments in scope; NULL means every department.
    departments: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)), nullable=True)
    # [{"department": "qc", "name": "...", "employee_id": "..."}]
    department_contacts: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    # How many SOPs / deviation reports had their content checked.
    content_documents_checked: Mapped[int | None] = mapped_column(Integer, nullable=True)

    items: Mapped[list["AuditSimulationRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AuditSimulationRunItem.position"
    )
    content_findings: Mapped[list["AuditSimulationContentFinding"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AuditSimulationContentFinding.position"
    )

    @property
    def run_code(self) -> str:
        return f"SIM-{self.run_number:04d}"

    @property
    def total(self) -> int:
        return (self.missing or 0) + (self.incomplete or 0) + (self.satisfied or 0)

    # Content gaps still open, i.e. not dismissed as false positives in review.
    @property
    def content_critical(self) -> int:
        return sum(1 for f in self.content_findings if f.severity == "critical" and f.decision != "false_positive")

    @property
    def content_major(self) -> int:
        return sum(1 for f in self.content_findings if f.severity == "major" and f.decision != "false_positive")

    @property
    def content_unreviewed(self) -> int:
        return sum(1 for f in self.content_findings if f.decision is None)


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


class AuditSimulationContentFinding(Base):
    """A content gap found in one of the run's SOPs or deviation reports:
    a regulatory requirement the document doesn't (fully) address. The
    second half of the internal audit, alongside AuditSimulationRunItem's
    "does the record exist?" check. Frozen like run items (text copied, not
    linked); the review decision is the only part that changes afterwards."""

    __tablename__ = "audit_simulation_content_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audit_simulation_runs.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str] = mapped_column(String(32), nullable=False)
    document_title: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)  # sop | deviation
    regulation: Mapped[str] = mapped_column(String(32), nullable=False)
    clause_number: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_title: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # missing | partial
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # critical | major
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Review of the finding (keyword matching can be wrong).
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)  # confirmed|false_positive|needs_sme
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[AuditSimulationRun] = relationship(back_populates="content_findings")

    @property
    def citation(self) -> str:
        names = {"qmsr": "QMSR", "iso13485": "ISO 13485", "cfr211": "21 CFR"}
        return f"{names.get(self.regulation, self.regulation.upper())} {self.clause_number}"
