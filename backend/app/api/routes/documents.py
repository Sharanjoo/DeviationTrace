import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import CurrentOrg, get_current_org
from app.core.storage import save_upload
from app.database import get_db
from app.models.document import Document
from app.schemas.document import DocumentDetailOut, DocumentOut, DocumentStatusOut

router = APIRouter(prefix="/documents", tags=["documents"])

VALID_TYPES = {"sop", "deviation", "batch_record"}


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
    """Stub: real classify -> extract -> cross-check pipeline is Milestone 2/3.
    This just marks the document queued so the frontend's processing screen has
    a real status to poll."""
    document = _get_org_document(document_id, current, db)
    document.status = "queued"
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
