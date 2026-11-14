"""Show what an AI review looks like, without calling an AI model.

Run from backend/ (API database up, migrations applied):

    python -m app.seed.ai_demo --email demo@acme.example.com

Uploads the demo SOP (SOP-QA-014) into the account's organization if it isn't
there, runs an internal audit over it, then stores a SIMULATED AI review of
that SOP: hand-written verdicts, saved the same way a real response would be.
Nothing is sent anywhere and nothing is charged.

The prompt recorded in the AI activity log is the real one the app would
send (built by the same code). The response is the hand-written one below,
and the log entry says so: its model is "simulated (no AI call was made)".
The quotes go through the real quote check, so one deliberately altered quote
shows the "not found in the text sent" warning.

It also turns AI assistance on for the organization so the results show. If
no provider has been set up, "Send for AI review" will fail with a message
until an admin adds one on Company profile.
"""

import argparse
import json
import sys

from fastapi.testclient import TestClient

from app.core.ai.content_review import VERDICTS, evidence_verified, prepare
from app.core.audit_simulation.content_check import citation, requirement_title
from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models import AiInteraction, AuditSimulationAiAssessment, AuditSimulationRun, Document, Organization, OrgAiSettings
from app.models.user import User
from app.seed.demo_documents import DEFAULT_OUTPUT_DIR

SOP = "SOP-QA-014_Control_of_Nonconforming_Product.docx"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SIMULATED_MODEL = "simulated (no AI call was made)"
AUDIT = {
    "title": "QA internal audit: AI review example",
    "audit_type": "internal_audit",
    "objective": "Show an AI review next to the rule-based content check.",
    "lead_name": "Priya Raman",
    "lead_employee_id": "EMP-1042",
    "lead_title": "QA Manager",
    "departments": ["qa"],
}

# Keyed by citation. Two of these disagree with the keyword check on purpose
# (it passes them; a careful reader wouldn't), and the QMSR 8.3.1 quote is
# slightly reworded so the quote check flags it.
SIMULATED = {
    "ISO 13485 8.2.3": (
        "partly_addressed",
        "Trends in deviations feed the site quality feedback process and give management early warning of quality problems.",
        "The SOP says deviation trends give early warning, but it doesn't say how feedback or complaint data is routed "
        "into corrective and preventive action. SOP-QA-022 is only listed as a reference; no step sends anything to it.",
    ),
    "ISO 13485 8.3.1": (
        "addressed",
        "It establishes the procedure to define the controls, responsibilities and authorities for the control of nonconforming product, from first detection through final disposition.",
        "The purpose states the controls, and sections 3 and 4 assign responsibilities and authorities for identifying "
        "and controlling nonconforming product.",
    ),
    "ISO 13485 8.3.2": (
        "addressed",
        "Disposition may include action to eliminate the nonconformity through rework or reprocessing, authorizing use under concession with documented approval of the quality control unit, or action to preclude original intended use by scrapping the material.",
        "All three disposition routes the requirement lists are covered, and concession needs documented approval.",
    ),
    "ISO 13485 8.3.4": (
        "not_addressed",
        "",
        "Nothing in the excerpts covers product found to be nonconforming after delivery or after use has begun: no "
        "action proportionate to the effects, no records of such action, and no advisory notices. The scope mentions "
        "returned product, but the procedure gives no steps for it.",
    ),
    "QMSR 8.2.2": (
        "partly_addressed",
        "Deviations that originate from a customer complaint shall be entered in the complaint file and handled under the complaint handling procedure, SOP-QA-031.",
        "Complaints are filed and handed to SOP-QA-031, and QA assesses whether an event is serious and unexpected. But "
        "the SOP doesn't link that assessment to the FDA reporting obligation: it doesn't say who reports, or when.",
    ),
    "QMSR 8.3.1": (
        "addressed",
        "Confirmed nonconforming product must be tagged and moved to quarantine so it is segregated from released stock.",
        "Identification (lot, quantity, location), documentation (deviation form and log), evaluation, segregation and "
        "disposition are all covered, with Quality Assurance responsible for review and disposition.",
    ),
    "QMSR 8.3.2": (
        "addressed",
        "Quality Assurance shall decide whether an investigation is needed. The deviation record shall state whether an investigation was conducted and, where none was performed, justify that decision.",
        "The need for an investigation is determined and documented with its rationale, and the responsible department "
        "head is notified of the nonconformance.",
    ),
}


def _user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        sys.exit(f"No active account with email {email}")
    if user.role == "viewer":
        sys.exit(f"{email} is a viewer and can't upload documents or run simulations")
    return user


def _run_with_sop(client: TestClient, headers: dict) -> tuple[str, str]:
    """A fresh internal audit run that content-checked the demo SOP."""
    existing = next((d for d in client.get("/documents", headers=headers).json() if d["title"] == SOP), None)
    if existing is None:
        path = DEFAULT_OUTPUT_DIR / SOP
        if not path.exists():
            sys.exit(f"Demo document not found: {path}. Run `python -m app.seed.demo_documents` first.")
        existing = client.post(
            "/documents",
            headers=headers,
            data={"type": "sop", "process_area": "deviation_handling", "department": "qa"},
            files={"file": (SOP, path.read_bytes(), DOCX)},
        ).json()
        client.post(f"/documents/{existing['id']}/process", headers=headers)
    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT)
    draft.raise_for_status()
    run = client.post(f"/audit-simulation/runs/{draft.json()['id']}/execute", headers=headers)
    run.raise_for_status()
    return run.json()["id"], existing["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = _user(db, args.email)
        headers = {"Authorization": f"Bearer {create_access_token(org_id=user.org_id, user_id=user.id)}"}
        run_id, document_id = _run_with_sop(TestClient(app), headers)

        run = db.get(AuditSimulationRun, run_id)
        document = db.get(Document, document_id)
        organization = db.get(Organization, user.org_id)

        settings = db.get(OrgAiSettings, user.org_id)
        if settings is None:
            settings = OrgAiSettings(org_id=user.org_id)
            db.add(settings)
        settings.enabled = True

        prepared = prepare(db, document, organization.industry, None, redact_identifiers=True)
        response = {
            "assessments": [
                {"requirement_id": rid, "verdict": verdict, "evidence": evidence, "reasoning": reasoning}
                for rid, clause in prepared.requirements
                if citation(clause) in SIMULATED
                for verdict, evidence, reasoning in [SIMULATED[citation(clause)]]
            ]
        }
        interaction = AiInteraction(
            org_id=user.org_id,
            user_id=user.id,
            user_name=f"{user.full_name or user.email} (demo seed)",
            purpose="content_review",
            run_id=run.id,
            document_id=document.id,
            document_title=document.title,
            provider=settings.provider,
            model_requested=settings.model,
            model_used=SIMULATED_MODEL,
            sections_sent=[{"heading": s.heading, "characters": len(s.text)} for s in prepared.sections],
            redacted=True,
            redaction_count=prepared.redaction_count,
            system_prompt=prepared.system,
            user_prompt=prepared.user,
            response_text=json.dumps(response, indent=2),
            status="success",
            request_id="simulated-demo",
        )
        db.add(interaction)
        db.flush()
        by_id = dict(prepared.requirements)
        for item in response["assessments"]:
            clause = by_id[item["requirement_id"]]
            assert item["verdict"] in VERDICTS
            evidence = item["evidence"] or None
            db.add(
                AuditSimulationAiAssessment(
                    run_id=run.id,
                    interaction_id=interaction.id,
                    document_id=document.id,
                    document_title=document.title,
                    citation=citation(clause),
                    requirement_title=requirement_title(clause),
                    verdict=item["verdict"],
                    evidence=evidence,
                    evidence_verified=bool(evidence) and evidence_verified(evidence, prepared.sent_document_text),
                    reasoning=item["reasoning"],
                )
            )
        db.commit()
        print(f"Simulated AI review stored for {len(response['assessments'])} requirements.")
        print(f"Open: /audit-simulation/runs/{run_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
