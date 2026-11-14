from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.onboarding.scope_templates import SCOPE_TEMPLATES
from app.core.security import CurrentOrg, get_current_org
from app.database import get_db
from app.models.audit_checklist_item import AuditChecklistItem
from app.models.organization import Organization
from app.schemas.onboarding import (
    AdoptResult,
    OnboardingStatusOut,
    ScopeTemplateDetailOut,
    ScopeTemplateSummaryOut,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/scope-templates", response_model=list[ScopeTemplateSummaryOut])
def list_scope_templates() -> list[ScopeTemplateSummaryOut]:
    return [
        ScopeTemplateSummaryOut(
            scope_category=t.scope_category,
            industry=t.industry,
            label=t.label,
            description=t.description,
        )
        for t in SCOPE_TEMPLATES.values()
    ]


@router.get("/scope-templates/{scope_category}", response_model=ScopeTemplateDetailOut)
def get_scope_template(scope_category: str) -> ScopeTemplateDetailOut:
    template = SCOPE_TEMPLATES.get(scope_category)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope template not found")
    return ScopeTemplateDetailOut(
        scope_category=template.scope_category,
        industry=template.industry,
        label=template.label,
        description=template.description,
        source_note=template.source_note,
        checklist_items=[
            {
                "department": i.department,
                "item_name": i.item_name,
                "citation": i.citation,
                "requirement_text": i.requirement_text,
                "match_phrases": list(i.match_phrases),
            }
            for i in template.checklist_items
        ],
        vendor_standards=[
            {
                "vendor_category": s.vendor_category,
                "requirement_name": s.requirement_name,
                "citation": s.citation,
                "requirement_text": s.requirement_text,
                "match_phrases": list(s.match_phrases),
            }
            for s in template.vendor_standards
        ],
    )


@router.post("/scope-templates/{scope_category}/adopt", response_model=AdoptResult)
def adopt_scope_template(
    scope_category: str,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AdoptResult:
    """Clone a scope template's checklist items into this org's own custom
    checklist (org_id set), so it shows up in /audit-simulation/checklist
    ready to run the internal audit simulation against. Skips items the org
    already effectively has — either its own prior custom item, or a global
    library item with the same (department, item_name) — so a template that
    happens to share names with the global library (several do, since both
    describe real overlapping ISO 13485/QMSR requirements) doesn't create a
    confusing duplicate sitting right next to the global item it restates."""
    template = SCOPE_TEMPLATES.get(scope_category)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope template not found")

    existing = {
        (item.department, item.item_name)
        for item in db.query(AuditChecklistItem)
        .filter(or_(AuditChecklistItem.org_id == current.org_id, AuditChecklistItem.org_id.is_(None)))
        .all()
    }

    added = 0
    for template_item in template.checklist_items:
        key = (template_item.department, template_item.item_name)
        if key in existing:
            continue
        db.add(
            AuditChecklistItem(
                org_id=current.org_id,
                department=template_item.department,
                item_name=template_item.item_name,
                citation=template_item.citation,
                requirement_text=template_item.requirement_text,
                match_phrases=list(template_item.match_phrases),
            )
        )
        added += 1

    _mark_onboarded(db, current, scope_category=template.scope_category)
    db.commit()
    return AdoptResult(added=added, skipped=len(template.checklist_items) - added)


def _mark_onboarded(db: Session, current: CurrentOrg, scope_category: str | None) -> Organization:
    """Record onboarding as done. The first completion time is kept, and the
    scope is only overwritten when a template was actually chosen."""
    org = db.get(Organization, current.org_id)
    if org.onboarded_at is None:
        org.onboarded_at = datetime.now(timezone.utc)
    if scope_category is not None:
        org.scope_category = scope_category
    return org


def _status(org: Organization) -> OnboardingStatusOut:
    template = SCOPE_TEMPLATES.get(org.scope_category) if org.scope_category else None
    return OnboardingStatusOut(
        completed=org.onboarded_at is not None,
        onboarded_at=org.onboarded_at,
        org_name=org.name,
        industry=org.industry,
        scope_category=org.scope_category,
        scope_label=template.label if template else None,
    )


@router.get("/status", response_model=OnboardingStatusOut)
def get_onboarding_status(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> OnboardingStatusOut:
    return _status(db.get(Organization, current.org_id))


@router.post("/complete", response_model=OnboardingStatusOut)
def complete_onboarding_with_standard_checklist(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> OnboardingStatusOut:
    """Finish onboarding without adopting a template: the org keeps the
    standard (global) checklist only."""
    org = _mark_onboarded(db, current, scope_category=None)
    db.commit()
    db.refresh(org)
    return _status(org)
