"""Vendors and their audits.

A vendor audit is one supplier audit report, uploaded for a specific vendor
and cross-checked against the standards for the vendor's category. The
cross-check itself is shared with POST /vendor-audit/{document_id}/run
(see vendor_audit.cross_check_document)."""

import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.documents import ALLOWED_EXTENSIONS, process_document
from app.api.routes.vendor_audit import cross_check_document
from app.core.security import CurrentOrg, get_current_org
from app.core.storage import save_upload
from app.database import get_db
from app.models.document import Document
from app.models.organization import Organization
from app.models.vendor import Vendor, VendorAudit
from app.models.vendor_audit_finding import VendorAuditFinding
from app.models.vendor_standard import VendorStandard
from app.schemas.vendor import (
    AssignReportIn,
    UnassignedReportOut,
    VendorAuditDetailOut,
    VendorAuditFindingRowOut,
    VendorAuditSummaryOut,
    VendorAuditUpdate,
    VendorCreate,
    VendorDetailOut,
    VendorOut,
)

router = APIRouter(tags=["vendors"])

_STATUS_ORDER = {"missing": 0, "partial": 1, "satisfied": 2}


# ------------------------------------------------------------------ helpers


def _counts_by_document(db: Session, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    counts: dict[uuid.UUID, dict[str, int]] = defaultdict(lambda: {"missing": 0, "partial": 0, "satisfied": 0})
    if document_ids:
        rows = (
            db.query(VendorAuditFinding.document_id, VendorAuditFinding.status, func.count())
            .filter(VendorAuditFinding.document_id.in_(document_ids))
            .group_by(VendorAuditFinding.document_id, VendorAuditFinding.status)
            .all()
        )
        for document_id, status_, n in rows:
            counts[document_id][status_] = n
    return counts


def _summary(audit: VendorAudit, counts: dict[str, int]) -> VendorAuditSummaryOut:
    return VendorAuditSummaryOut(
        id=audit.id,
        audit_number=audit.audit_number,
        audit_code=audit.audit_code,
        vendor_id=audit.vendor.id,
        vendor_name=audit.vendor.name,
        vendor_category=audit.vendor.vendor_category,
        audit_date=audit.audit_date,
        auditor_name=audit.auditor_name,
        auditor_employee_id=audit.auditor_employee_id,
        notes=audit.notes,
        created_at=audit.created_at,
        document_id=audit.document.id,
        document_title=audit.document.title,
        document_status=audit.document.status,
        processing_error=audit.document.processing_error,
        total=sum(counts.values()),
        **counts,
    )


def _summaries(db: Session, audits: list[VendorAudit]) -> list[VendorAuditSummaryOut]:
    counts = _counts_by_document(db, [a.document_id for a in audits])
    return [_summary(a, counts[a.document_id]) for a in audits]


def _vendor_out(db: Session, vendor: Vendor, detail: bool = False):
    summaries = _summaries(db, list(vendor.audits))  # newest first (relationship order)
    fields = dict(
        id=vendor.id,
        name=vendor.name,
        vendor_category=vendor.vendor_category,
        contact_name=vendor.contact_name,
        contact_email=vendor.contact_email,
        notes=vendor.notes,
        created_at=vendor.created_at,
        audit_count=len(summaries),
        latest_audit=summaries[0] if summaries else None,
    )
    return VendorDetailOut(**fields, audits=summaries) if detail else VendorOut(**fields)


def _get_vendor(db: Session, org_id: uuid.UUID, vendor_id: uuid.UUID) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None or vendor.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


def _get_audit(db: Session, org_id: uuid.UUID, audit_id: uuid.UUID) -> VendorAudit:
    audit = db.get(VendorAudit, audit_id)
    if audit is None or audit.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor audit not found")
    return audit


def _next_audit_number(db: Session, org_id: uuid.UUID) -> int:
    # Lock the org row so concurrent audits can't take the same number.
    db.query(Organization).filter(Organization.id == org_id).with_for_update().one()
    last = db.query(func.max(VendorAudit.audit_number)).filter(VendorAudit.org_id == org_id).scalar()
    return (last or 0) + 1


def _cross_check_if_processed(db: Session, document_id: uuid.UUID) -> None:
    document = db.query(Document).filter(Document.id == document_id).with_for_update().one()
    if document.status == "processed":
        cross_check_document(db, document)


def _unassigned_query(db: Session, org_id: uuid.UUID):
    linked = db.query(VendorAudit.document_id)
    return db.query(Document).filter(
        Document.org_id == org_id,
        Document.type == "vendor_audit_report",
        Document.id.notin_(linked),
    )


# ------------------------------------------------------------------ vendors


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)) -> list[VendorOut]:
    vendors = db.query(Vendor).filter(Vendor.org_id == current.org_id).order_by(Vendor.name).all()
    return [_vendor_out(db, v) for v in vendors]


@router.post("/vendors", response_model=VendorDetailOut, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> VendorDetailOut:
    vendor = Vendor(org_id=current.org_id, **payload.model_dump())
    db.add(vendor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A vendor with this name already exists") from exc
    db.refresh(vendor)
    return _vendor_out(db, vendor, detail=True)


@router.get("/vendors/unassigned-reports", response_model=list[UnassignedReportOut])
def list_unassigned_reports(
    current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)
) -> list[Document]:
    """Vendor audit reports not linked to any vendor yet (uploaded before
    vendors existed, or through the generic upload)."""
    return _unassigned_query(db, current.org_id).order_by(Document.uploaded_at.desc()).all()


@router.get("/vendors/{vendor_id}", response_model=VendorDetailOut)
def get_vendor(
    vendor_id: uuid.UUID, current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)
) -> VendorDetailOut:
    return _vendor_out(db, _get_vendor(db, current.org_id, vendor_id), detail=True)


@router.post("/vendors/{vendor_id}/audits", response_model=VendorAuditDetailOut, status_code=status.HTTP_201_CREATED)
def create_vendor_audit(
    vendor_id: uuid.UUID,
    file: UploadFile = File(...),
    auditor_name: str = Form(...),
    auditor_employee_id: str = Form(...),
    audit_date: date | None = Form(default=None),
    notes: str | None = Form(default=None),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> VendorAuditDetailOut:
    """New audit for a vendor in one step: upload its audit report, read it,
    and cross-check it against the vendor category's standards."""
    vendor = _get_vendor(db, current.org_id, vendor_id)
    auditor_name, auditor_employee_id = auditor_name.strip(), auditor_employee_id.strip()
    if not auditor_name or not auditor_employee_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Auditor name and employee ID are required"
        )
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"file extension must be one of {ALLOWED_EXTENSIONS}",
        )

    document = Document(
        org_id=current.org_id,
        type="vendor_audit_report",
        title=file.filename or "untitled",
        process_area="general",
        vendor_category=vendor.vendor_category,
        file_ref=save_upload(current.org_id, file.filename or "upload", file.file.read()),
        status="uploaded",
    )
    db.add(document)
    db.flush()
    audit = VendorAudit(
        org_id=current.org_id,
        vendor_id=vendor.id,
        document_id=document.id,
        audit_number=_next_audit_number(db, current.org_id),
        audit_date=audit_date,
        auditor_name=auditor_name,
        auditor_employee_id=auditor_employee_id,
        notes=(notes or "").strip() or None,
    )
    db.add(audit)
    db.commit()

    # Read the report (a failure is recorded on the document, not raised),
    # then cross-check it if that worked.
    process_document(document.id, current, db)
    _cross_check_if_processed(db, document.id)
    db.commit()
    return get_vendor_audit(audit.id, current, db)


@router.post("/vendors/{vendor_id}/assign-report", response_model=VendorAuditDetailOut, status_code=status.HTTP_201_CREATED)
def assign_report_to_vendor(
    vendor_id: uuid.UUID,
    payload: AssignReportIn,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> VendorAuditDetailOut:
    """Attach an unassigned vendor audit report to a vendor as one of its
    audits. The report takes the vendor's category and is re-checked."""
    vendor = _get_vendor(db, current.org_id, vendor_id)
    document = _unassigned_query(db, current.org_id).filter(Document.id == payload.document_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unassigned vendor audit report not found")

    document.vendor_category = vendor.vendor_category
    audit = VendorAudit(
        org_id=current.org_id,
        vendor_id=vendor.id,
        document_id=document.id,
        audit_number=_next_audit_number(db, current.org_id),
        audit_date=payload.audit_date or document.uploaded_at.date(),
        auditor_name=payload.auditor_name,
        auditor_employee_id=payload.auditor_employee_id,
    )
    db.add(audit)
    db.flush()
    _cross_check_if_processed(db, document.id)
    db.commit()
    return get_vendor_audit(audit.id, current, db)


# ------------------------------------------------------------------ audits


@router.get("/vendor-audits/{audit_id}", response_model=VendorAuditDetailOut)
def get_vendor_audit(
    audit_id: uuid.UUID, current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)
) -> VendorAuditDetailOut:
    audit = _get_audit(db, current.org_id, audit_id)
    rows = (
        db.query(VendorAuditFinding, VendorStandard)
        .join(VendorStandard, VendorAuditFinding.standard_id == VendorStandard.id)
        .filter(VendorAuditFinding.document_id == audit.document_id)
        .all()
    )
    rows.sort(key=lambda r: (_STATUS_ORDER.get(r[0].status, 9), r[1].requirement_name))
    summary = _summaries(db, [audit])[0]
    return VendorAuditDetailOut(
        **summary.model_dump(),
        findings=[
            VendorAuditFindingRowOut(
                id=finding.id,
                requirement_name=standard.requirement_name,
                citation=standard.citation,
                requirement_text=standard.requirement_text,
                status=finding.status,
                severity=finding.severity,
                explanation=finding.explanation,
            )
            for finding, standard in rows
        ],
    )


@router.post("/vendor-audits/{audit_id}/rerun", response_model=VendorAuditDetailOut)
def rerun_vendor_audit(
    audit_id: uuid.UUID, current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)
) -> VendorAuditDetailOut:
    """Cross-check the audit's report again (e.g. after the standards library
    changed)."""
    audit = _get_audit(db, current.org_id, audit_id)
    if audit.document.status != "processed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The audit report could not be read")
    _cross_check_if_processed(db, audit.document_id)
    db.commit()
    return get_vendor_audit(audit.id, current, db)


@router.patch("/vendor-audits/{audit_id}", response_model=VendorAuditDetailOut)
def update_vendor_audit(
    audit_id: uuid.UUID,
    payload: VendorAuditUpdate,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> VendorAuditDetailOut:
    """Correct an audit's date, auditor or notes (e.g. an older report that
    was attached with its upload date). Results are unaffected."""
    audit = _get_audit(db, current.org_id, audit_id)
    # Only fields actually sent are changed; send null/blank to clear one.
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(audit, key, value)
    db.commit()
    return get_vendor_audit(audit.id, current, db)
