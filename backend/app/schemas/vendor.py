import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

VENDOR_CATEGORIES = {
    "raw_material_supplier",
    "contract_manufacturer",
    "calibration_test_service",
    "sterilization_service",
    "packaging_component_supplier",
}


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class VendorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    vendor_category: str
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("is required")
        return value

    @field_validator("contact_name", "contact_email", "notes", mode="before")
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)

    @field_validator("vendor_category")
    @classmethod
    def _category(cls, value: str) -> str:
        if value not in VENDOR_CATEGORIES:
            raise ValueError(f"must be one of {sorted(VENDOR_CATEGORIES)}")
        return value


class AssignReportIn(BaseModel):
    document_id: uuid.UUID
    audit_date: date | None = None
    auditor_name: str | None = Field(default=None, max_length=255)
    auditor_employee_id: str | None = Field(default=None, max_length=64)

    @field_validator("auditor_name", "auditor_employee_id", mode="before")
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)


class VendorAuditUpdate(BaseModel):
    """Editable details of a vendor audit. The report itself (and so its
    results) can't be swapped; start a new audit for a new report."""

    audit_date: date | None = None
    # Optional, like when attaching an older report: the auditor of a past
    # audit isn't always known.
    auditor_name: str | None = Field(default=None, max_length=255)
    auditor_employee_id: str | None = Field(default=None, max_length=64)
    notes: str | None = None

    @field_validator("auditor_name", "auditor_employee_id", "notes", mode="before")
    @classmethod
    def _optional(cls, value):
        return _blank_to_none(value)


class VendorAuditSummaryOut(BaseModel):
    id: uuid.UUID
    audit_number: int
    audit_code: str
    vendor_id: uuid.UUID
    vendor_name: str
    vendor_category: str
    audit_date: date | None
    auditor_name: str | None
    auditor_employee_id: str | None
    notes: str | None
    created_at: datetime
    document_id: uuid.UUID
    document_title: str
    document_status: str
    processing_error: str | None
    # Cross-check results; all zero until the report has been checked.
    missing: int
    partial: int
    satisfied: int
    total: int


class VendorAuditFindingRowOut(BaseModel):
    id: uuid.UUID
    requirement_name: str
    citation: str
    requirement_text: str
    status: str
    severity: str
    explanation: str


class VendorDocumentationIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    field: str
    context: str
    location: str | None
    confidence: str


class VendorAuditDetailOut(VendorAuditSummaryOut):
    findings: list[VendorAuditFindingRowOut]
    # Blank signatures, dates, entries or placeholders in the vendor's report.
    documentation_issues: list[VendorDocumentationIssueOut]


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    vendor_category: str
    contact_name: str | None
    contact_email: str | None
    notes: str | None
    created_at: datetime
    audit_count: int
    latest_audit: VendorAuditSummaryOut | None


class VendorDetailOut(VendorOut):
    audits: list[VendorAuditSummaryOut]


class UnassignedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    vendor_category: str | None
    status: str
    uploaded_at: datetime
