import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload

from app.core.security import CurrentOrg, get_current_org
from app.core.vendor_audit.base import VendorAuditFindingData
from app.core.vendor_audit.rule_based import RuleBasedVendorAuditEngine
from app.database import get_db
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.vendor_audit_finding import VendorAuditFinding
from app.models.vendor_standard import VendorStandard
from app.schemas.vendor_audit import VendorAuditFindingOut, VendorAuditRunResult

router = APIRouter(prefix="/vendor-audit", tags=["vendor-audit"])

_SEVERITY_RANK = case(
    (VendorAuditFinding.severity == "critical", 0),
    (VendorAuditFinding.severity == "major", 1),
    else_=2,
)


def _get_org_document(document_id: uuid.UUID, current: CurrentOrg, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _upsert_vendor_audit_findings(db: Session, document_id: uuid.UUID, new_findings: list[VendorAuditFindingData]) -> None:
    """Update-in-place by standard_id rather than delete-all-then-reinsert,
    same reprocess-safety lesson as documents.py's _upsert_findings — though
    no TriageDecision-equivalent exists yet for this table, so stale rows can
    be deleted outright."""
    existing_by_standard = {
        f.standard_id: f for f in db.query(VendorAuditFinding).filter(VendorAuditFinding.document_id == document_id).all()
    }
    seen_standard_ids: set[uuid.UUID] = set()

    for data in new_findings:
        seen_standard_ids.add(data.standard_id)
        existing = existing_by_standard.get(data.standard_id)
        if existing:
            existing.section_id = data.section_id
            existing.status = data.status
            existing.severity = data.severity
            existing.explanation = data.explanation
        else:
            db.add(
                VendorAuditFinding(
                    document_id=document_id,
                    section_id=data.section_id,
                    standard_id=data.standard_id,
                    status=data.status,
                    severity=data.severity,
                    explanation=data.explanation,
                )
            )

    for standard_id, existing in existing_by_standard.items():
        if standard_id not in seen_standard_ids:
            db.delete(existing)


@router.post("/{document_id}/run", response_model=VendorAuditRunResult)
def run_vendor_audit(
    document_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> VendorAuditRunResult:
    """Re-evaluate one vendor audit report document's content against every
    VendorStandard for its vendor_category, and upsert findings in place."""
    document = _get_org_document(document_id, current, db)
    if document.type != "vendor_audit_report":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document type must be 'vendor_audit_report'",
        )
    if document.vendor_category is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="document has no vendor_category")

    # Lock, mirroring documents.py's process_document: two near-simultaneous
    # /run calls for the same document (double-click, client retry) must not
    # both read "no existing findings" and both insert.
    document = db.query(Document).filter(Document.id == document.id).with_for_update().one()
    if document.status != "processed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="document must be processed (POST /documents/{id}/process) before running the vendor-audit cross-check",
        )

    counts = cross_check_document(db, document)
    db.commit()
    return VendorAuditRunResult(**counts)


def cross_check_document(db: Session, document: Document) -> dict[str, int]:
    """Check a processed vendor audit report against every VendorStandard for
    its vendor_category and upsert the findings in place. The caller holds
    the document row lock and commits. Shared by POST /vendor-audit/{id}/run
    and the vendor audit flow in vendors.py."""
    sections = (
        db.query(DocumentSection)
        .filter(DocumentSection.document_id == document.id)
        .order_by(DocumentSection.order)
        .all()
    )
    standards = db.query(VendorStandard).filter(VendorStandard.vendor_category == document.vendor_category).all()

    results = RuleBasedVendorAuditEngine().evaluate(document, sections, standards)
    _upsert_vendor_audit_findings(db, document.id, results)

    counts = {"missing": 0, "partial": 0, "satisfied": 0}
    for data in results:
        counts[data.status] += 1
    return counts


@router.get("/findings", response_model=list[VendorAuditFindingOut])
def list_vendor_audit_findings(
    document_id: uuid.UUID | None = Query(default=None),
    vendor_category: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[VendorAuditFinding]:
    query = (
        db.query(VendorAuditFinding)
        .join(Document, VendorAuditFinding.document_id == Document.id)
        .join(VendorStandard, VendorAuditFinding.standard_id == VendorStandard.id)
        .filter(Document.org_id == current.org_id)
        .options(
            joinedload(VendorAuditFinding.document),
            joinedload(VendorAuditFinding.section),
            joinedload(VendorAuditFinding.standard),
        )
    )
    if document_id:
        query = query.filter(VendorAuditFinding.document_id == document_id)
    if vendor_category:
        query = query.filter(Document.vendor_category == vendor_category)
    if status_:
        query = query.filter(VendorAuditFinding.status == status_)
    return query.order_by(Document.vendor_category, _SEVERITY_RANK, VendorStandard.requirement_name).all()
