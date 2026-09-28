from fastapi import APIRouter, Depends, Query
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload

from app.core.audit_simulation.rule_based import RuleBasedAuditSimulationEngine
from app.core.security import CurrentOrg, get_current_org
from app.database import get_db
from app.models.audit_checklist_finding import AuditChecklistFinding
from app.models.audit_checklist_item import AuditChecklistItem
from app.models.document import Document
from app.schemas.audit_simulation import AuditChecklistFindingOut, AuditSimulationRunResult

router = APIRouter(prefix="/audit-simulation", tags=["audit-simulation"])

_SEVERITY_RANK = case(
    (AuditChecklistFinding.severity == "critical", 0),
    (AuditChecklistFinding.severity == "major", 1),
    else_=2,
)


@router.post("/run", response_model=AuditSimulationRunResult)
def run_audit_simulation(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRunResult:
    """Re-evaluate every checklist item against the org's current documents
    and upsert in place (never delete-and-recreate — same lesson as the
    document reprocess FK bug in the base system's matching engine)."""
    documents = (
        db.query(Document)
        .filter(Document.org_id == current.org_id, Document.department.isnot(None))
        .options(joinedload(Document.sections))
        .all()
    )
    checklist_items = db.query(AuditChecklistItem).all()

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
