import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.reporting import generate_summary_pdf
from app.core.security import CurrentOrg, get_current_org
from app.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{org_id}/export")
def export_report(
    org_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Response:
    if org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot export another organization's report")

    pdf_bytes = generate_summary_pdf(db, org_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=deviationtrace-report.pdf"},
    )
