import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.core.security import CurrentOrg, get_current_org
from app.database import get_db
from app.models.document import Document
from app.models.finding import Finding
from app.models.regulatory_clause import RegulatoryClause
from app.models.triage_decision import TriageDecision
from app.schemas.finding import FindingOut, TriageOut, TriageRequest

router = APIRouter(tags=["findings"])

_SEVERITY_RANK = case(
    (Finding.severity == "critical", 0),
    (Finding.severity == "major", 1),
    (Finding.severity == "minor", 2),
    else_=3,
)


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    document_id: uuid.UUID | None = Query(default=None),
    severity: str | None = Query(default=None),
    clause_id: uuid.UUID | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    triage: Literal["pending", "confirmed", "false_positive", "needs_sme"] | None = Query(default=None),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[Finding]:
    query = (
        db.query(Finding)
        .join(Document, Finding.document_id == Document.id)
        .join(RegulatoryClause, Finding.clause_id == RegulatoryClause.id)
        .filter(Document.org_id == current.org_id)
        .options(
            joinedload(Finding.section),
            joinedload(Finding.clause),
            joinedload(Finding.document),
            joinedload(Finding.triage_decision),
        )
    )
    if document_id:
        query = query.filter(Finding.document_id == document_id)
    if severity:
        query = query.filter(Finding.severity == severity)
    if clause_id:
        query = query.filter(Finding.clause_id == clause_id)
    if status_:
        query = query.filter(Finding.status == status_)
    if triage == "pending":
        query = query.filter(~Finding.triage_decision.has())
    elif triage:
        query = query.filter(Finding.triage_decision.has(TriageDecision.decision == triage))
    return query.order_by(
        _SEVERITY_RANK, Document.title, RegulatoryClause.regulation, RegulatoryClause.clause_number, Finding.id
    ).all()


@router.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(
    finding_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Finding:
    finding = (
        db.query(Finding)
        .join(Document, Finding.document_id == Document.id)
        .filter(Finding.id == finding_id, Document.org_id == current.org_id)
        .options(
            joinedload(Finding.section),
            joinedload(Finding.clause),
            joinedload(Finding.document),
            joinedload(Finding.triage_decision),
        )
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding


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
        existing.user_id = current.user_id
        existing.decided_at = func.now()
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
