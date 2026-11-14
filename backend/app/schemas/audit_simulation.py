import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.document import DocumentSummaryOut


class AuditChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    item_name: str
    citation: str
    requirement_text: str


class AuditChecklistFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklist_item: AuditChecklistItemOut
    matched_document: DocumentSummaryOut | None
    status: str
    severity: str
    explanation: str
    evaluated_at: datetime


class AuditSimulationRunResult(BaseModel):
    missing: int
    incomplete: int
    satisfied: int
    # The history entry this run was saved as.
    run_id: uuid.UUID
    run_number: int
    run_code: str


AUDIT_TYPES = {
    "internal_audit",
    "mock_fda_inspection",
    "certification_readiness",
    "customer_audit_prep",
    "for_cause",
}
_DEPARTMENTS = {"qc", "qa", "utilities", "manufacturing", "engineering"}


class DepartmentContact(BaseModel):
    department: str
    name: str = ""
    employee_id: str = ""

    @field_validator("name", "employee_id")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class AuditDetailsIn(BaseModel):
    """Step 1 of a new simulation: what audit this is, who leads it, and
    which departments (and their owners) are in scope."""

    title: str = Field(min_length=1, max_length=255)
    audit_type: str
    planned_date: date | None = None
    lead_name: str = Field(min_length=1, max_length=255)
    lead_employee_id: str = Field(min_length=1, max_length=64)
    lead_title: str | None = Field(default=None, max_length=255)
    lead_email: EmailStr | None = None
    objective: str | None = None
    departments: list[str] = Field(min_length=1)
    department_contacts: list[DepartmentContact] = []

    @field_validator("title", "lead_name", "lead_employee_id")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("is required")
        return value

    @field_validator("lead_title", "objective", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("lead_email", mode="before")
    @classmethod
    def _blank_email_to_none(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("audit_type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        if value not in AUDIT_TYPES:
            raise ValueError(f"must be one of {sorted(AUDIT_TYPES)}")
        return value

    @field_validator("departments")
    @classmethod
    def _known_departments(cls, value: list[str]) -> list[str]:
        unknown = set(value) - _DEPARTMENTS
        if unknown:
            raise ValueError(f"unknown departments: {sorted(unknown)}")
        # De-duplicate, keeping the standard department order.
        return [d for d in ["qc", "qa", "utilities", "manufacturing", "engineering"] if d in value]

    @model_validator(mode="after")
    def _contacts_in_scope(self):
        for contact in self.department_contacts:
            if contact.department not in self.departments:
                raise ValueError(f"contact given for department not in scope: {contact.department}")
        return self


class AuditSimulationRunSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_number: int
    run_code: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    missing: int | None
    incomplete: int | None
    satisfied: int | None
    total: int
    title: str | None
    audit_type: str | None
    planned_date: date | None
    lead_name: str | None
    lead_employee_id: str | None
    lead_title: str | None
    lead_email: str | None
    objective: str | None
    departments: list[str] | None
    department_contacts: list[DepartmentContact] | None
    # Content check (SOPs and deviation reports)
    content_documents_checked: int | None
    content_critical: int
    content_major: int
    content_unreviewed: int
    documentation_issue_count: int


class AuditSimulationRunItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    item_name: str
    citation: str
    status: str
    severity: str
    explanation: str
    matched_document_title: str | None


REVIEW_DECISIONS = {"confirmed", "false_positive", "needs_sme"}


class ContentFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    document_title: str
    document_type: str
    citation: str
    requirement_title: str
    requirement_text: str
    section_heading: str | None
    status: str
    severity: str
    explanation: str
    decision: str | None
    decision_note: str | None
    decided_by: str | None
    decided_at: datetime | None


class ContentFindingReviewIn(BaseModel):
    # None clears the decision (back to "not reviewed").
    decision: str | None
    note: str | None = None

    @field_validator("decision")
    @classmethod
    def _known(cls, value: str | None) -> str | None:
        if value is not None and value not in REVIEW_DECISIONS:
            raise ValueError(f"must be one of {sorted(REVIEW_DECISIONS)}")
        return value


class DocumentationIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    field: str
    context: str
    location: str | None
    confidence: str


class RunDocumentationIssueOut(DocumentationIssueOut):
    department: str
    document_title: str


class AuditSimulationRunDetailOut(AuditSimulationRunSummaryOut):
    items: list[AuditSimulationRunItemOut]
    content_findings: list[ContentFindingOut]
    documentation_issues: list[RunDocumentationIssueOut]


class EffectiveChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department: str
    item_name: str
    citation: str
    requirement_text: str
    match_phrases: list[str]
    is_custom: bool
    is_excluded: bool


class ChecklistItemCreate(BaseModel):
    department: str
    item_name: str
    citation: str
    requirement_text: str
    match_phrases: list[str] = []
