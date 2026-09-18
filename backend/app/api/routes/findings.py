import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import CurrentOrg, get_current_org
from app.database import get_db
from app.models.document import Document
from app.models.finding import Finding
from app.models.triage_decision import TriageDecision
from app.schemas.finding import FindingOut, TriageOut, TriageRequest

router = APIRouter(tags=["findings"])


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    document_id: uuid.UUID | None = Query(default=None),
    severity: str | None = Query(default=None),
    clause_id: uuid.UUID | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[Finding]:
    query = (
        db.query(Finding)
        .join(Document, Finding.document_id == Document.id)
        .filter(Document.org_id == current.org_id)
        .options(joinedload(Finding.section), joinedload(Finding.clause))
    )
    if document_id:
        query = query.filter(Finding.document_id == document_id)
    if severity:
        query = query.filter(Finding.severity == severity)
    if clause_id:
        query = query.filter(Finding.clause_id == clause_id)
    if status_:
        query = query.filter(Finding.status == status_)
    return query.all()


@router.post("/findings/{finding_id}/triage", response_model=TriageOut, status_code=status.HTTP_201_CREATED)
def triage_finding(
    finding_id: uuid.UUID,
    payload: TriageRequest,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> TriageDecision:
    finding = (
        db.query(Finding)
        .join(Document, Finding.document_id == Document.id)
        .filter(Finding.id == finding_id, Document.org_id == current.org_id)
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    existing = db.query(TriageDecision).filter(TriageDecision.finding_id == finding_id).first()
    if existing is not None:
        existing.decision = payload.decision
        existing.note = payload.note
        decision = existing
    else:
        decision = TriageDecision(
            finding_id=finding_id,
            user_id=current.user_id,
            decision=payload.decision,
            note=payload.note,
        )
        db.add(decision)

    db.commit()
    db.refresh(decision)
    return decision
