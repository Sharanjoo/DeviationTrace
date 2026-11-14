"""Optional AI assistance: organization settings, AI content review of a
run's SOPs and deviation reports, and the full activity log.

- Settings: anyone signed in can see whether AI is on; only admins change
  it. The provider API key is stored encrypted and never returned.
- Review: members choose which sections to send and whether to remove
  identifiers, can preview exactly what will be sent, then send it.
- Log: admins can see every AI call, including the exact text sent.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.ai import content_review
from app.core.ai.crypto import encrypt_secret
from app.core.ai.providers import DEFAULT_MODEL, PROVIDERS, missing_configuration
from app.core.security import CurrentOrg, get_current_org, require_admin
from app.database import get_db
from app.models.ai import AiInteraction, AuditSimulationAiAssessment, OrgAiSettings
from app.models.audit_simulation_run import AuditSimulationRun
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User
from app.schemas.ai import (
    AiAssessmentOut,
    AiInteractionDetailOut,
    AiInteractionSummaryOut,
    AiPreviewOut,
    AiReviewOut,
    AiReviewRequest,
    AiSettingsIn,
    AiSettingsOut,
    RequirementOut,
    SectionOut,
)

router = APIRouter(tags=["ai"])


def _settings(db: Session, org_id: uuid.UUID) -> OrgAiSettings:
    settings = db.get(OrgAiSettings, org_id)
    if settings is None:
        settings = OrgAiSettings(org_id=org_id, enabled=False, provider="anthropic", model=DEFAULT_MODEL, redact_identifiers=True)
    return settings


def _settings_out(settings: OrgAiSettings) -> AiSettingsOut:
    return AiSettingsOut(
        enabled=settings.enabled,
        provider=settings.provider,
        model=settings.model,
        region=settings.region,
        project_id=settings.project_id,
        resource=settings.resource,
        api_key_set=bool(settings.api_key_encrypted),
        redact_identifiers=settings.redact_identifiers,
        updated_at=settings.updated_at,
        updated_by=settings.updated_by,
        missing_configuration=missing_configuration(settings),
        providers=PROVIDERS,
    )


# ------------------------------------------------------------------ settings


@router.get("/org/ai-settings", response_model=AiSettingsOut)
def get_ai_settings(current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)) -> AiSettingsOut:
    return _settings_out(_settings(db, current.org_id))


@router.put("/org/ai-settings", response_model=AiSettingsOut)
def update_ai_settings(
    payload: AiSettingsIn, current: CurrentOrg = Depends(require_admin), db: Session = Depends(get_db)
) -> AiSettingsOut:
    if payload.provider not in PROVIDERS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown AI provider")
    settings = db.get(OrgAiSettings, current.org_id)
    if settings is None:
        settings = OrgAiSettings(org_id=current.org_id)
        db.add(settings)
    settings.provider = payload.provider
    settings.model = payload.model
    settings.region = payload.region
    settings.project_id = payload.project_id
    settings.resource = payload.resource
    settings.redact_identifiers = payload.redact_identifiers
    if payload.api_key is not None:
        settings.api_key_encrypted = encrypt_secret(payload.api_key.strip()) if payload.api_key.strip() else None
    # Only allow turning AI on once the chosen provider is fully configured.
    if payload.enabled and (problem := missing_configuration(settings)):
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problem)
    settings.enabled = payload.enabled
    user = db.get(User, current.user_id)
    settings.updated_by = user.full_name or user.email
    db.commit()
    db.refresh(settings)
    return _settings_out(settings)


# ------------------------------------------------------------------ review


def _review_target(db: Session, current: CurrentOrg, run_id: uuid.UUID, document_id: uuid.UUID):
    settings = _settings(db, current.org_id)
    if not settings.enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI assistance is turned off for your organization.")
    run = db.get(AuditSimulationRun, run_id)
    if run is None or run.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run not found")
    if not any(d["id"] == str(document_id) for d in run.content_documents or []):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That document wasn't content-checked in this run"
        )
    document = db.get(Document, document_id)
    if document is None or document.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    industry = db.get(Organization, current.org_id).industry
    return settings, run, document, industry


@router.post("/audit-simulation/runs/{run_id}/documents/{document_id}/ai-preview", response_model=AiPreviewOut)
def preview_ai_review(
    run_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: AiReviewRequest,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AiPreviewOut:
    """Show exactly what would be sent, for the chosen sections and
    redaction setting. Sends nothing."""
    settings, _run, document, industry = _review_target(db, current, run_id, document_id)
    redact = settings.redact_identifiers if payload.redact is None else payload.redact
    try:
        prepared = content_review.prepare(db, document, industry, payload.section_ids, redact)
    except content_review.ReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    sections = sorted(document.sections, key=lambda s: s.order)
    return AiPreviewOut(
        document_title=document.title,
        provider=settings.provider,
        provider_label=PROVIDERS[settings.provider],
        model=settings.model,
        sections=[
            SectionOut(id=s.id, heading=s.heading, characters=len(s.text), preview=" ".join(s.text.split())[:240])
            for s in sections
        ],
        selected_section_ids=[s.id for s in prepared.sections],
        redact=redact,
        redaction_count=prepared.redaction_count,
        requirements=[
            RequirementOut(citation=content_review.citation(c), title=content_review.requirement_title(c))
            for _, c in prepared.requirements
        ],
        system_prompt=prepared.system,
        user_prompt=prepared.user,
    )


@router.post("/audit-simulation/runs/{run_id}/documents/{document_id}/ai-review", response_model=AiReviewOut)
def review_with_ai(
    run_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: AiReviewRequest,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> AiReviewOut:
    """Send the chosen sections for AI review. Logged in full whatever the
    outcome; the verdicts are stored alongside the rule-based results."""
    settings, run, document, industry = _review_target(db, current, run_id, document_id)
    user = db.get(User, current.user_id)
    redact = settings.redact_identifiers if payload.redact is None else payload.redact
    try:
        interaction = content_review.run_review(
            db, settings, run, document, industry, payload.section_ids, redact, user.id, user.full_name or user.email
        )
    except content_review.ReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    assessments = (
        db.query(AuditSimulationAiAssessment)
        .filter(AuditSimulationAiAssessment.interaction_id == interaction.id)
        .all()
    )
    return AiReviewOut(
        interaction=AiInteractionSummaryOut.model_validate(interaction),
        assessments=[AiAssessmentOut.model_validate(a) for a in assessments],
    )


@router.get("/audit-simulation/runs/{run_id}/ai-assessments", response_model=list[AiAssessmentOut])
def list_ai_assessments(
    run_id: uuid.UUID, current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)
) -> list[AuditSimulationAiAssessment]:
    """The latest AI review of each document in the run."""
    run = db.get(AuditSimulationRun, run_id)
    if run is None or run.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run not found")
    rows = (
        db.query(AuditSimulationAiAssessment)
        .filter(AuditSimulationAiAssessment.run_id == run_id)
        .order_by(AuditSimulationAiAssessment.created_at.desc())
        .all()
    )
    latest_interaction: dict[str, uuid.UUID] = {}
    for row in rows:
        latest_interaction.setdefault(row.document_title, row.interaction_id)
    return [r for r in reversed(rows) if latest_interaction[r.document_title] == r.interaction_id]


# ------------------------------------------------------------------ activity log


@router.get("/org/ai-log", response_model=list[AiInteractionSummaryOut])
def list_ai_interactions(current: CurrentOrg = Depends(require_admin), db: Session = Depends(get_db)) -> list[AiInteraction]:
    return (
        db.query(AiInteraction)
        .filter(AiInteraction.org_id == current.org_id)
        .order_by(AiInteraction.created_at.desc())
        .limit(500)
        .all()
    )


@router.get("/org/ai-log/{interaction_id}", response_model=AiInteractionDetailOut)
def get_ai_interaction(
    interaction_id: uuid.UUID, current: CurrentOrg = Depends(require_admin), db: Session = Depends(get_db)
) -> AiInteraction:
    interaction = db.get(AiInteraction, interaction_id)
    if interaction is None or interaction.org_id != current.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return interaction
