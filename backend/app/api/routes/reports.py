import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentOrg, get_current_org

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{org_id}/export")
def export_report(org_id: uuid.UUID, current: CurrentOrg = Depends(get_current_org)) -> None:
    """Stub: PDF export is Milestone 4 (packaged for the SME review session)."""
    if org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot export another organization's report")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Report export is not implemented until Milestone 4",
    )
