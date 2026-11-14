import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.routes.documents import VALID_DEPARTMENTS
from app.core.audit_simulation.content_check import (
    CONTENT_DOCUMENT_TYPES,
    check_document_content,
    requirement_title,
)
from app.core.audit_simulation.rule_based import RuleBasedAuditSimulationEngine
from app.core.reporting import generate_audit_run_pdf
from app.core.security import CurrentOrg, get_current_org
from app.database import get_db
from app.models.audit_checklist_finding import AuditChecklistFinding
from app.models.audit_checklist_item import AuditChecklistItem
from app.models.audit_simulation_run import (
    AuditSimulationContentFinding,
    AuditSimulationRun,
    AuditSimulationRunItem,
)
from app.models.document import Document
from app.models.org_checklist_exclusion import OrgChecklistExclusion
from app.models.organization import Organization
from app.models.user import User
from app.schemas.audit_simulation import (
    AuditChecklistFindingOut,
    AuditDetailsIn,
    AuditSimulationRunDetailOut,
    AuditSimulationRunResult,
    AuditSimulationRunSummaryOut,
    ChecklistItemCreate,
    ContentFindingOut,
    ContentFindingReviewIn,
    EffectiveChecklistItemOut,
)

router = APIRouter(prefix="/audit-simulation", tags=["audit-simulation"])

_SEVERITY_RANK = case(
    (AuditChecklistFinding.severity == "critical", 0),
    (AuditChecklistFinding.severity == "major", 1),
    else_=2,
)


def _effective_items_query(db: Session, org_id: uuid.UUID):
    """Global items (org_id IS NULL) not excluded by this org, plus the
    org's own custom items (org_id == org_id)."""
    excluded_ids = db.query(OrgChecklistExclusion.checklist_item_id).filter(OrgChecklistExclusion.org_id == org_id)
    return db.query(AuditChecklistItem).filter(
        or_(AuditChecklistItem.org_id == org_id, AuditChecklistItem.org_id.is_(None)),
        AuditChecklistItem.id.notin_(excluded_ids),
    )


_DEPARTMENT_ORDER = {d: i for i, d in enumerate(["qc", "qa", "utilities", "manufacturing", "engineering"])}
_STATUS_ORDER = {"missing": 0, "incomplete": 1, "satisfied": 2}


def _lock_org(db: Session, org_id: uuid.UUID) -> None:
    """Serialize run creation/execution per org: two simultaneous requests
    (double-click, retry) would otherwise race on the finding upserts and
    on the next run_number."""
    db.query(Organization).filter(Organization.id == org_id).with_for_update().one()


def _new_run(db: Session, org_id: uuid.UUID, **fields) -> AuditSimulationRun:
    last = (
        db.query(func.max(AuditSimulationRun.run_number)).filter(AuditSimulationRun.org_id == org_id).scalar()
    ) or 0
    run = AuditSimulationRun(org_id=org_id, run_number=last + 1, **fields)
    db.add(run)
    return run


def _execute(db: Session, org_id: uuid.UUID, run: AuditSimulationRun) -> dict[str, int]:
    """Evaluate the org's effective checklist (limited to the run's
    departments, if it has any) against its current documents; upsert the
    current findings in place (never delete-and-recreate, same lesson as the
    document reprocess FK bug); and freeze the results into the run."""
    documents = (
        db.query(Document)
        .filter(Document.org_id == org_id, Document.department.isnot(None))
        .options(joinedload(Document.sections))
        .all()
    )
    effective_items = _effective_items_query(db, org_id).all()
    in_scope = [i for i in effective_items if not run.departments or i.department in run.departments]

    results = RuleBasedAuditSimulationEngine().evaluate(documents, in_scope)

    existing_by_item = {
        f.checklist_item_id: f
        for f in db.query(AuditChecklistFinding).filter(AuditChecklistFinding.org_id == org_id).all()
    }
    counts = {"missing": 0, "incomplete": 0, "satisfied": 0}
    for data in results:
        counts[data.status] += 1
        existing = existing_by_item.get(data.checklist_item_id)
        if existing:
            existing.matched_document_id = data.matched_document_id
            existing.status = data.status
            existing.severity = data.severity
            existing.explanation = data.explanation
        else:
            db.add(
                AuditChecklistFinding(
                    org_id=org_id,
                    checklist_item_id=data.checklist_item_id,
                    matched_document_id=data.matched_document_id,
                    status=data.status,
                    severity=data.severity,
                    explanation=data.explanation,
                )
            )

    # Drop findings for items no longer on this org's effective checklist
    # (excluded since the last run). Out-of-scope departments keep their
    # last result. Safe to delete outright: nothing references
    # AuditChecklistFinding (no triage on this table yet).
    effective_ids = {item.id for item in effective_items}
    for item_id, existing in existing_by_item.items():
        if item_id not in effective_ids:
            db.delete(existing)

    items_by_id = {item.id: item for item in in_scope}
    titles_by_id = {doc.id: doc.title for doc in documents}
    rows = sorted(
        results,
        key=lambda r: (
            _DEPARTMENT_ORDER.get(items_by_id[r.checklist_item_id].department, 99),
            _STATUS_ORDER.get(r.status, 9),
            items_by_id[r.checklist_item_id].item_name,
        ),
    )
    for position, data in enumerate(rows):
        item = items_by_id[data.checklist_item_id]
        run.items.append(
            AuditSimulationRunItem(
                position=position,
                department=item.department,
                item_name=item.item_name,
                citation=item.citation,
                status=data.status,
                severity=data.severity,
                explanation=data.explanation,
                matched_document_title=titles_by_id.get(data.matched_document_id),
            )
        )

    _record_content_gaps(db, run, [d for d in documents if not run.departments or d.department in run.departments])

    run.missing, run.incomplete, run.satisfied = counts["missing"], counts["incomplete"], counts["satisfied"]
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.flush()
    return counts


_SEVERITY_ORDER = {"critical": 0, "major": 1}


def _record_content_gaps(db: Session, run: AuditSimulationRun, documents: list[Document]) -> None:
    """Content half of the audit: check each in-scope SOP and deviation
    report against its regulatory requirements and freeze the gaps into the
    run (see content_check.py)."""
    checked = [d for d in documents if d.type in CONTENT_DOCUMENT_TYPES and d.status == "processed"]
    industry = db.get(Organization, run.org_id).industry
    rows = []
    for document in checked:
        for gap in check_document_content(db, document, industry):
            rows.append((document, gap))
    rows.sort(
        key=lambda r: (
            _DEPARTMENT_ORDER.get(r[0].department, 99),
            r[0].title,
            _SEVERITY_ORDER.get(r[1].severity, 9),
            requirement_title(r[1].clause),
        )
    )
    for position, (document, gap) in enumerate(rows):
        run.content_findings.append(
            AuditSimulationContentFinding(
                position=position,
                department=document.department,
                document_title=document.title,
                document_type=document.type,
                regulation=gap.clause.regulation,
                clause_number=gap.clause.clause_number,
                requirement_title=requirement_title(gap.clause),
                requirement_text=gap.clause.requirement_text,
                section_heading=gap.section_heading,
                status=gap.status,
                severity=gap.severity,
                explanation=gap.explanation,
            )
        )
    run.content_documents_checked = len(checked)


@router.post("/run", response_model=AuditSimulationRunResult)
def run_audit_simulation(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRunResult:
    """Quick run: every department, no audit details. The app's main flow is
    POST /audits (details) -> upload documents -> POST /runs/{id}/execute."""
    _lock_org(db, current.org_id)
    run = _new_run(db, current.org_id, status="completed")
    counts = _execute(db, current.org_id, run)
    db.commit()
    return AuditSimulationRunResult(**counts, run_id=run.id, run_number=run.run_number, run_code=run.run_code)


def _details_fields(payload: AuditDetailsIn) -> dict:
    fields = payload.model_dump()
    # Keep only contacts someone actually filled in.
    fields["department_contacts"] = [c for c in fields["department_contacts"] if c["name"] or c["employee_id"]]
    return fields


@router.post("/audits", response_model=AuditSimulationRunDetailOut, status_code=status.HTTP_201_CREATED)
def start_audit(
    payload: AuditDetailsIn,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRun:
    """Step 1 of a new simulation: record the audit's details as a draft run
    (its SIM number is assigned now). Documents are uploaded next, then the
    run is executed with POST /runs/{id}/execute."""
    _lock_org(db, current.org_id)
    run = _new_run(db, current.org_id, status="draft", **_details_fields(payload))
    db.commit()
    db.refresh(run)
    return run


def _get_draft(db: Session, org_id: uuid.UUID, run_id: uuid.UUID) -> AuditSimulationRun:
    run = _get_org_run(db, org_id, run_id)
    if run.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This simulation has already been run")
    return run


def _get_org_run(db: Session, org_id: uuid.UUID, run_id: uuid.UUID) -> AuditSimulationRun:
    run = db.get(AuditSimulationRun, run_id)
    if run is None or run.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run not found")
    return run


@router.get("/runs", response_model=list[AuditSimulationRunSummaryOut])
def list_audit_simulation_runs(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[AuditSimulationRun]:
    """Every run for this org, newest first."""
    return (
        db.query(AuditSimulationRun)
        .filter(AuditSimulationRun.org_id == current.org_id)
        .order_by(AuditSimulationRun.run_number.desc())
        .all()
    )


@router.get("/runs/{run_id}", response_model=AuditSimulationRunDetailOut)
def get_audit_simulation_run(
    run_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRun:
    return _get_org_run(db, current.org_id, run_id)


@router.get("/runs/{run_id}/report")
def download_audit_simulation_run_report(
    run_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> Response:
    """PDF report for one run, built from its frozen results, so it reads the
    same no matter when it's downloaded."""
    run = _get_org_run(db, current.org_id, run_id)
    if run.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Run the simulation before generating its report"
        )
    org = db.get(Organization, current.org_id)
    pdf_bytes = generate_audit_run_pdf(org, run)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=deviationtrace-{run.run_code}.pdf"},
    )


@router.get("/findings", response_model=list[AuditChecklistFindingOut])
def list_audit_simulation_findings(
    department: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[AuditChecklistFinding]:
    query = (
        db.query(AuditChecklistFinding)
        .join(AuditChecklistItem, AuditChecklistFinding.checklist_item_id == AuditChecklistItem.id)
        .filter(AuditChecklistFinding.org_id == current.org_id)
        .options(
            joinedload(AuditChecklistFinding.checklist_item),
            joinedload(AuditChecklistFinding.matched_document),
        )
    )
    if department:
        query = query.filter(AuditChecklistItem.department == department)
    if status_:
        query = query.filter(AuditChecklistFinding.status == status_)
    return query.order_by(AuditChecklistItem.department, _SEVERITY_RANK, AuditChecklistItem.item_name).all()


@router.get("/checklist", response_model=list[EffectiveChecklistItemOut])
def list_effective_checklist(
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[EffectiveChecklistItemOut]:
    """The org's actual working checklist: every global item (flagged
    whether this org has excluded it) plus every custom item this org has
    added, department by department. This is the "build it department-wise"
    view an existing company edits — distinct from /findings, which is the
    result of running the simulation against that checklist."""
    excluded_ids = {
        row.checklist_item_id
        for row in db.query(OrgChecklistExclusion).filter(OrgChecklistExclusion.org_id == current.org_id).all()
    }
    items = (
        db.query(AuditChecklistItem)
        .filter(or_(AuditChecklistItem.org_id == current.org_id, AuditChecklistItem.org_id.is_(None)))
        .order_by(AuditChecklistItem.department, AuditChecklistItem.item_name)
        .all()
    )
    return [
        EffectiveChecklistItemOut(
            id=item.id,
            department=item.department,
            item_name=item.item_name,
            citation=item.citation,
            requirement_text=item.requirement_text,
            match_phrases=item.match_phrases,
            is_custom=item.org_id is not None,
            is_excluded=item.id in excluded_ids,
        )
        for item in items
    ]


@router.post("/checklist", response_model=EffectiveChecklistItemOut, status_code=status.HTTP_201_CREATED)
def add_custom_checklist_item(
    payload: ChecklistItemCreate,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> EffectiveChecklistItemOut:
    if payload.department not in VALID_DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"department must be one of {VALID_DEPARTMENTS}"
        )
    item = AuditChecklistItem(
        org_id=current.org_id,
        department=payload.department,
        item_name=payload.item_name,
        citation=payload.citation,
        requirement_text=payload.requirement_text,
        match_phrases=payload.match_phrases,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return EffectiveChecklistItemOut(
        id=item.id,
        department=item.department,
        item_name=item.item_name,
        citation=item.citation,
        requirement_text=item.requirement_text,
        match_phrases=item.match_phrases,
        is_custom=True,
        is_excluded=False,
    )


@router.delete("/checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_checklist_item(
    item_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    item = db.get(AuditChecklistItem, item_id)
    if item is None or item.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom checklist item not found")
    # Its findings reference it by FK, so remove them first or the delete
    # fails once the simulation has run against this item.
    db.query(AuditChecklistFinding).filter(AuditChecklistFinding.checklist_item_id == item.id).delete()
    db.delete(item)
    db.commit()


@router.post("/checklist/{item_id}/exclude", status_code=status.HTTP_204_NO_CONTENT)
def exclude_global_checklist_item(
    item_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    item = db.get(AuditChecklistItem, item_id)
    if item is None or item.org_id is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Global checklist item not found")
    existing = (
        db.query(OrgChecklistExclusion)
        .filter(OrgChecklistExclusion.org_id == current.org_id, OrgChecklistExclusion.checklist_item_id == item_id)
        .first()
    )
    if not existing:
        db.add(OrgChecklistExclusion(org_id=current.org_id, checklist_item_id=item_id))
    # Clear this org's prior finding for the item right away, so the
    # findings list reflects the exclusion without waiting for a re-run.
    db.query(AuditChecklistFinding).filter(
        AuditChecklistFinding.org_id == current.org_id, AuditChecklistFinding.checklist_item_id == item_id
    ).delete()
    db.commit()


@router.delete("/checklist/{item_id}/exclude", status_code=status.HTTP_204_NO_CONTENT)
def include_global_checklist_item(
    item_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    db.query(OrgChecklistExclusion).filter(
        OrgChecklistExclusion.org_id == current.org_id, OrgChecklistExclusion.checklist_item_id == item_id
    ).delete()
    db.commit()


@router.patch("/runs/{run_id}", response_model=AuditSimulationRunDetailOut)
def update_audit_details(
    run_id: uuid.UUID,
    payload: AuditDetailsIn,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRun:
    """Edit a draft's audit details. Completed runs are frozen."""
    run = _get_draft(db, current.org_id, run_id)
    for key, value in _details_fields(payload).items():
        setattr(run, key, value)
    db.commit()
    db.refresh(run)
    return run


@router.post("/runs/{run_id}/execute", response_model=AuditSimulationRunDetailOut)
def execute_audit(
    run_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationRun:
    """Final step: run the simulation for a draft against the documents on
    file now, and freeze the results into it."""
    _lock_org(db, current.org_id)
    run = _get_draft(db, current.org_id, run_id)
    _execute(db, current.org_id, run)
    db.commit()
    db.refresh(run)
    return run


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_draft_audit(
    run_id: uuid.UUID,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    """Discard a draft that was never run. Completed runs are permanent
    history and can't be deleted. Uploaded documents are kept."""
    run = _get_draft(db, current.org_id, run_id)
    db.delete(run)
    db.commit()


@router.post("/runs/{run_id}/content-findings/{finding_id}/review", response_model=ContentFindingOut)
def review_content_finding(
    run_id: uuid.UUID,
    finding_id: uuid.UUID,
    payload: ContentFindingReviewIn,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AuditSimulationContentFinding:
    """Record a reviewer's decision on a content gap (keyword matching can
    be wrong, so an SME confirms or dismisses each one). The finding itself
    stays frozen; only the decision changes."""
    run = _get_org_run(db, current.org_id, run_id)
    finding = db.get(AuditSimulationContentFinding, finding_id)
    if finding is None or finding.run_id != run.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    user = db.get(User, current.user_id)
    finding.decision = payload.decision
    finding.decision_note = (payload.note or "").strip() or None
    finding.decided_by = (user.full_name or user.email) if payload.decision else None
    finding.decided_at = datetime.now(timezone.utc) if payload.decision else None
    db.commit()
    db.refresh(finding)
    return finding
