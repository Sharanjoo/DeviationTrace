from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.regulatory_clause import RegulatoryClause
from app.schemas.clause import RegulatoryClauseOut

router = APIRouter(prefix="/clauses", tags=["clauses"])


@router.get("", response_model=list[RegulatoryClauseOut])
def list_clauses(
    regulation: str | None = Query(default=None),
    process_area: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RegulatoryClause]:
    query = db.query(RegulatoryClause)
    if regulation:
        query = query.filter(RegulatoryClause.regulation == regulation)
    if process_area:
        query = query.filter(RegulatoryClause.process_area == process_area)
    return query.order_by(RegulatoryClause.regulation, RegulatoryClause.clause_number).all()
