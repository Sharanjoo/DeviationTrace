import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from app.api.routes.documents import VALID_DEPARTMENTS
from app.core.audit_simulation.rule_based import RuleBasedAuditSimulationEngine
from app.core.security import CurrentOrg, get_current_org
from app.database import get_db
from app.models.audit_checklist_finding import AuditChecklistFinding
from app.models.audit_checklist_item import AuditChecklistItem
from app.models.document import Document
from app.models.org_checklist_exclusion import OrgChecklistExclusion
from app.schemas.audit_simulation import (
    AuditChecklistFindingOut,
    AuditSimulationRunResult,
    ChecklistItemCreate,
    EffectiveChecklistItemOut,
)

router = APIRouter(prefix="/audit-simulation", tags=["audit-simulation"])

_SEVERITY_RANK = case(
    (AuditChecklistFinding.severity == "critical", 0),
    (AuditChecklistFinding.severity == "major", 1),
    else_=2,
)


def _effective_items_query(db: Session, org_id: uuid.UUID):
    """Global items (org_id IS NULL) not excluded by this org, plus the
    org's own custom items (org_id == org_id)."""
    excluded_ids = db.query(OrgChecklistExclusion.checklist_item_id).filter(OrgChecklistExclusion.org_id == org_id)
    return db.query(AuditChecklistItem).filter(
        or_(AuditChecklistItem.org_id == org_id, AuditChecklistItem.org_id.is_(None)),
        AuditChecklistItem.id.notin_(excluded_ids),
    )


@router.post("/run", response_model=AuditSimulationRunResult)
def run_audit_simulation(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRunResult:
    """Re-evaluate every checklist item effective for this org (global items
    it hasn't excluded, plus its own custom items) against its current
    documents, and upsert in place (never delete-and-recreate — same lesson
    as the document reprocess FK bug in the base system's matching engine)."""
    documents = (
        db.query(Document)
        .filter(Document.org_id == current.org_id, Document.department.isnot(None))
        .options(joinedload(Document.sections))
        .all()
    )
    checklist_items = _effective_items_query(db, current.org_id).all()

    engine = RuleBasedAuditSimulationEngine()
    results = engine.evaluate(documents, checklist_items)

    existing_by_item = {
        f.checklist_item_id: f
        for f in db.query(AuditChecklistFinding).filter(AuditChecklistFinding.org_id == current.org_id).all()
    }

    counts = {"missing": 0, "incomplete": 0, "satisfied": 0}
    for data in results:
        counts[data.status] += 1
        existing = existing_by_item.get(data.checklist_item_id)
        if existing:
            existing.matched_document_id = data.matched_document_id
            existing.status = data.status
            existing.severity = data.severity
            existing.explanation = data.explanation
        else:
            db.add(
                AuditChecklistFinding(
                    org_id=current.org_id,
                    checklist_item_id=data.checklist_item_id,
                    matched_document_id=data.matched_document_id,
                    status=data.status,
                    severity=data.severity,
                    explanation=data.explanation,
                )
            )

    # Drop findings for items no longer on this org's effective checklist
    # (excluded since the last run). Safe to delete outright: nothing
    # references AuditChecklistFinding (no triage on this table yet).
    evaluated_item_ids = {data.checklist_item_id for data in results}
    for item_id, existing in existing_by_item.items():
        if item_id not in evaluated_item_ids:
            db.delete(existing)

    db.commit()
    return AuditSimulationRunResult(**counts)


@router.get("/findings", response_model=list[AuditChecklistFindingOut])
def list_audit_simulation_findings(
    department: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[AuditChecklistFinding]:
    query = (
        db.query(AuditChecklistFinding)
        .join(AuditChecklistItem, AuditChecklistFinding.checklist_item_id == AuditChecklistItem.id)
        .filter(AuditChecklistFinding.org_id == current.org_id)
        .options(
            joinedload(AuditChecklistFinding.checklist_item),
            joinedload(AuditChecklistFinding.matched_document),
        )
    )
    if department:
        query = query.filter(AuditChecklistItem.department == department)
    if status_:
        query = query.filter(AuditChecklistFinding.status == status_)
    return query.order_by(AuditChecklistItem.department, _SEVERITY_RANK, AuditChecklistItem.item_name).all()


@router.get("/checklist", response_model=list[EffectiveChecklistItemOut])
def list_effective_checklist(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[EffectiveChecklistItemOut]:
    """The org's actual working checklist: every global item (flagged
    whether this org has excluded it) plus every custom item this org has
    added, department by department. This is the "build it department-wise"
    view an existing company edits — distinct from /findings, which is the
    result of running the simulation against that checklist."""
    excluded_ids = {
        row.checklist_item_id
        for row in db.query(OrgChecklistExclusion).filter(OrgChecklistExclusion.org_id == current.org_id).all()
    }
    items = (
        db.query(AuditChecklistItem)
        .filter(or_(AuditChecklistItem.org_id == current.org_id, AuditChecklistItem.org_id.is_(None)))
        .order_by(AuditChecklistItem.department, AuditChecklistItem.item_name)
        .all()
    )
    return [
        EffectiveChecklistItemOut(
            id=item.id,
            department=item.department,
            item_name=item.item_name,
            citation=item.citation,
            requirement_text=item.requirement_text,
            match_phrases=item.match_phrases,
            is_custom=item.org_id is not None,
            is_excluded=item.id in excluded_ids,
        )
        for item in items
    ]


@router.post("/checklist", response_model=EffectiveChecklistItemOut, status_code=status.HTTP_201_CREATED)
def add_custom_checklist_item(
    payload: ChecklistItemCreate,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> EffectiveChecklistItemOut:
    if payload.department not in VALID_DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"department must be one of {VALID_DEPARTMENTS}"
        )
    item = AuditChecklistItem(
        org_id=current.org_id,
        department=payload.department,
        item_name=payload.item_name,
        citation=payload.citation,
        requirement_text=payload.requirement_text,
        match_phrases=payload.match_phrases,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return EffectiveChecklistItemOut(
        id=item.id,
        department=item.department,
        item_name=item.item_name,
        citation=item.citation,
        requirement_text=item.requirement_text,
        match_phrases=item.match_phrases,
        is_custom=True,
        is_excluded=False,
    )


@router.delete("/checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_checklist_item(
    item_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    item = db.get(AuditChecklistItem, item_id)
    if item is None or item.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom checklist item not found")
    # Its findings reference it by FK, so remove them first or the delete
    # fails once the simulation has run against this item.
    db.query(AuditChecklistFinding).filter(AuditChecklistFinding.checklist_item_id == item.id).delete()
    db.delete(item)
    db.commit()


@router.post("/checklist/{item_id}/exclude", status_code=status.HTTP_204_NO_CONTENT)
def exclude_global_checklist_item(
    item_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    item = db.get(AuditChecklistItem, item_id)
    if item is None or item.org_id is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Global checklist item not found")
    existing = (
        db.query(OrgChecklistExclusion)
        .filter(OrgChecklistExclusion.org_id == current.org_id, OrgChecklistExclusion.checklist_item_id == item_id)
        .first()
    )
    if not existing:
        db.add(OrgChecklistExclusion(org_id=current.org_id, checklist_item_id=item_id))
    # Clear this org's prior finding for the item right away, so the
    # findings list reflects the exclusion without waiting for a re-run.
    db.query(AuditChecklistFinding).filter(
        AuditChecklistFinding.org_id == current.org_id, AuditChecklistFinding.checklist_item_id == item_id
    ).delete()
    db.commit()


@router.delete("/checklist/{item_id}/exclude", status_code=status.HTTP_204_NO_CONTENT)
def include_global_checklist_item(
    item_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    db.query(OrgChecklistExclusion).filter(
        OrgChecklistExclusion.org_id == current.org_id, OrgChecklistExclusion.checklist_item_id == item_id
    ).delete()
    db.commit()
