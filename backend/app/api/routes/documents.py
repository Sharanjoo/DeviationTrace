import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.matching.base import FindingData
from app.core.matching.rule_based import RuleBasedMatchingEngine
from app.core.parsing.pipeline import run_pipeline
from app.core.security import CurrentOrg, get_current_org
from app.core.storage import save_upload
from app.database import get_db
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.finding import Finding
from app.models.regulatory_clause import RegulatoryClause
from app.schemas.document import DocumentDetailOut, DocumentOut, DocumentStatusOut

router = APIRouter(prefix="/documents", tags=["documents"])

VALID_TYPES = {"sop", "deviation", "batch_record", "report", "vendor_audit_report"}
VALID_DEPARTMENTS = {"qc", "qa", "utilities", "manufacturing", "engineering"}
VALID_VENDOR_CATEGORIES = {
    "raw_material_supplier",
    "contract_manufacturer",
    "calibration_test_service",
    "sterilization_service",
    "packaging_component_supplier",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _get_org_document(document_id: uuid.UUID, current: CurrentOrg, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _upsert_findings(db: Session, document_id: uuid.UUID, new_findings: list[FindingData]) -> None:
    """Update-in-place by clause_id rather than delete-all-then-reinsert, so a
    reprocessed document doesn't orphan (or silently discard) a TriageDecision
    a QA user already recorded against a prior finding for the same clause."""
    existing_by_clause = {
        f.clause_id: f for f in db.query(Finding).filter(Finding.document_id == document_id).all()
    }
    seen_clause_ids: set[uuid.UUID] = set()

    for data in new_findings:
        seen_clause_ids.add(data.clause_id)
        existing = existing_by_clause.get(data.clause_id)
        if existing:
            existing.section_id = data.section_id
            existing.status = data.status
            existing.severity = data.severity
            existing.explanation = data.explanation
        else:
            db.add(
                Finding(
                    document_id=document_id,
                    section_id=data.section_id,
                    clause_id=data.clause_id,
                    status=data.status,
                    severity=data.severity,
                    explanation=data.explanation,
                )
            )

    for clause_id, existing in existing_by_clause.items():
        if clause_id not in seen_clause_ids and existing.triage_decision is None:
            db.delete(existing)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    type: str = Form(...),
    process_area: str = Form(...),
    department: str | None = Form(default=None),
    vendor_category: str | None = Form(default=None),
    file: UploadFile = File(...),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Document:
    if type not in VALID_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"type must be one of {VALID_TYPES}")
    if department is not None and department not in VALID_DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"department must be one of {VALID_DEPARTMENTS}"
        )
    if vendor_category is not None and vendor_category not in VALID_VENDOR_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"vendor_category must be one of {VALID_VENDOR_CATEGORIES}",
        )

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"file extension must be one of {ALLOWED_EXTENSIONS}",
        )

    content = file.file.read()
    file_ref = save_upload(current.org_id, file.filename or "upload", content)

    document = Document(
        org_id=current.org_id,
        type=type,
        title=file.filename or "untitled",
        process_area=process_area,
        department=department,
        vendor_category=vendor_category,
        file_ref=file_ref,
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Document:
    return _get_org_document(document_id, current, db)


@router.post("/{document_id}/process", response_model=DocumentStatusOut, status_code=status.HTTP_202_ACCEPTED)
def process_document(
    document_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Document:
    """Classify -> extract -> section-split -> rule-based cross-check, run
    synchronously (no Celery yet, per Milestone 1's infra decision —
    acceptable at the PRD's ~50-page demo scale)."""
    document = _get_org_document(document_id, current, db)

    document.status = "processing"
    document.processing_error = None
    db.commit()

    try:
        result = run_pipeline(document.file_ref, document.type)

        # Serialize concurrent /process calls for the same document (e.g. a
        # double-click, a client retry, or React StrictMode's dev double-invoke)
        # around the section/finding writes below. Without this lock, two
        # concurrent requests can both read "no existing rows" and both insert,
        # producing duplicate Finding rows instead of one updating the other.
        document = db.query(Document).filter(Document.id == document.id).with_for_update().one()

        # Reuse existing sections on reprocessing rather than delete + recreate:
        # file_ref is immutable once uploaded, so re-extracting the same file
        # always reproduces the same split, and Finding.section_id (plus, via
        # it, TriageDecision) may already reference these rows — deleting them
        # would violate that FK for any document that already has findings.
        persisted_sections: list[DocumentSection] = (
            db.query(DocumentSection)
            .filter(DocumentSection.document_id == document.id)
            .order_by(DocumentSection.order)
            .all()
        )
        if not persisted_sections:
            for section in result.sections:
                db_section = DocumentSection(
                    document_id=document.id,
                    heading=section.heading,
                    text=section.text,
                    order=section.order,
                    span_start=section.span_start,
                    span_end=section.span_end,
                )
                db.add(db_section)
                persisted_sections.append(db_section)
            db.flush()  # assign ids so findings can cite real section_ids

        applicable_clauses = (
            db.query(RegulatoryClause)
            .filter(
                RegulatoryClause.process_area == document.process_area,
                RegulatoryClause.document_type_applicability.any(document.type),
            )
            .all()
        )
        new_findings = RuleBasedMatchingEngine().evaluate(document, persisted_sections, applicable_clauses)
        _upsert_findings(db, document.id, new_findings)

        document.status = "processed"
        document.detected_process_area = result.detected_process_area
        db.commit()
    except Exception as exc:
        db.rollback()
        document = _get_org_document(document_id, current, db)
        document.status = "failed"
        document.processing_error = str(exc)
        db.commit()

    db.refresh(document)
    return document


@router.get("/{document_id}/status", response_model=DocumentStatusOut)
def get_document_status(
    document_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Document:
    return _get_org_document(document_id, current, db)
