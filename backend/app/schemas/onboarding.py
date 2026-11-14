from datetime import datetime

from pydantic import BaseModel


class ScopeTemplateSummaryOut(BaseModel):
    scope_category: str
    industry: str
    label: str
    description: str


class ChecklistItemTemplateOut(BaseModel):
    department: str
    item_name: str
    citation: str
    requirement_text: str
    match_phrases: list[str]


class VendorStandardTemplateOut(BaseModel):
    vendor_category: str
    requirement_name: str
    citation: str
    requirement_text: str
    match_phrases: list[str]


class ScopeTemplateDetailOut(BaseModel):
    scope_category: str
    industry: str
    label: str
    description: str
    source_note: str
    checklist_items: list[ChecklistItemTemplateOut]
    vendor_standards: list[VendorStandardTemplateOut]


class AdoptResult(BaseModel):
    added: int
    skipped: int


class OnboardingStatusOut(BaseModel):
    """What the app needs to decide whether to show onboarding, and the
    company profile it remembers once onboarding is done."""

    completed: bool
    onboarded_at: datetime | None
    org_name: str
    industry: str
    scope_category: str | None
    scope_label: str | None
