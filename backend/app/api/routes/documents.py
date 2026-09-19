import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.parsing.pipeline import run_pipeline
from app.core.security import CurrentOrg, get_current_org
from app.core.storage import save_upload
from app.database import get_db
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.schemas.document import DocumentDetailOut, DocumentOut, DocumentStatusOut

router = APIRouter(prefix="/documents", tags=["documents"])

VALID_TYPES = {"sop", "deviation", "batch_record"}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _get_org_document(document_id: uuid.UUID, current: CurrentOrg, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    type: str = Form(...),
    process_area: str = Form(...),
    file: UploadFile = File(...),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Document:
    if type not in VALID_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"type must be one of {VALID_TYPES}")

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
    """Classify -> extract -> section-split, run synchronously (no Celery yet,
    per Milestone 1's infra decision — acceptable at the PRD's ~50-page demo
    scale). The cross-check pass itself is Milestone 3."""
    document = _get_org_document(document_id, current, db)

    document.status = "processing"
    document.processing_error = None
    db.commit()

    try:
        result = run_pipeline(document.file_ref, document.type)
    except Exception as exc:
        document.status = "failed"
        document.processing_error = str(exc)
        db.commit()
        db.refresh(document)
        return document

    db.query(DocumentSection).filter(DocumentSection.document_id == document.id).delete()
    for section in result.sections:
        db.add(
            DocumentSection(
                document_id=document.id,
                heading=section.heading,
                text=section.text,
                order=section.order,
                span_start=section.span_start,
                span_end=section.span_end,
            )
        )

    document.status = "processed"
    document.detected_process_area = result.detected_process_area
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
