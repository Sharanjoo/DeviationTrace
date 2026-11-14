"""Set up the documentation completeness demo in an existing account.

Run from backend/ (API database up, migrations applied):

    python -m app.seed.documentation_demo --email demo@acme.example.com

Uploads the three documentation demo documents (see
documentation_demo_documents.py) into the account's organization, then
creates and runs an internal audit simulation covering their departments, so
the run's "Signatures, dates and blank fields" section and PDF show the
planted gaps.

Only adds data: documents already uploaded with the same file name are
reused, nothing is changed or deleted, and each run is a new simulation. It
acts as the given user through the normal API (with a token minted
server-side), so the account must be an active admin or member, and its
organization must have finished onboarding.
"""

import argparse
import sys

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database import SessionLocal
from app.main import app
from app.models.user import User
from app.seed.demo_documents import DEFAULT_OUTPUT_DIR
from app.seed.documentation_demo_documents import DOCUMENTATION_DEMO_DOCUMENTS, build_all

MIME = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}

AUDIT = {
    "title": "Pre-inspection documentation check",
    "audit_type": "mock_fda_inspection",
    "objective": "Find blank signatures, dates, stamps and unfilled fields before the inspection.",
    "lead_name": "Priya Raman",
    "lead_employee_id": "EMP-1042",
    "lead_title": "QA Manager",
    "departments": ["qa", "manufacturing", "engineering"],
    "department_contacts": [{"department": "manufacturing", "name": "J. Lee", "employee_id": "EMP-3307"}],
}


def _token_for(email: str) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None or not user.is_active:
            sys.exit(f"No active account with email {email}")
        if user.role == "viewer":
            sys.exit(f"{email} is a viewer and can't upload documents or run simulations")
        return create_access_token(org_id=user.org_id, user_id=user.id)
    finally:
        db.close()


def run(email: str) -> str:
    headers = {"Authorization": f"Bearer {_token_for(email)}"}
    client = TestClient(app)

    status = client.get("/onboarding/status", headers=headers).json()
    if not status.get("completed"):
        sys.exit(f"{status.get('org_name', 'The organization')} hasn't finished onboarding yet; log in once first.")

    if not all((DEFAULT_OUTPUT_DIR / name).exists() for name, _ in DOCUMENTATION_DEMO_DOCUMENTS):
        build_all()

    existing = {d["title"]: d for d in client.get("/documents", headers=headers).json()}
    for name, department in DOCUMENTATION_DEMO_DOCUMENTS:
        if name in existing and existing[name]["status"] == "processed":
            print(f"Already uploaded: {name}")
            continue
        path = DEFAULT_OUTPUT_DIR / name
        uploaded = client.post(
            "/documents",
            headers=headers,
            data={"type": "report", "process_area": "general", "department": department},
            files={"file": (name, path.read_bytes(), MIME[path.suffix])},
        )
        uploaded.raise_for_status()
        processed = client.post(f"/documents/{uploaded.json()['id']}/process", headers=headers).json()
        print(f"Uploaded {name} to {department}: {processed['status']}")

    draft = client.post("/audit-simulation/audits", headers=headers, json=AUDIT)
    draft.raise_for_status()
    result = client.post(f"/audit-simulation/runs/{draft.json()['id']}/execute", headers=headers)
    result.raise_for_status()
    run_ = result.json()
    print(
        f"Ran {run_['run_code']} '{run_['title']}' for {status['org_name']}: "
        f"{run_['documentation_issue_count']} documentation issue(s)"
    )
    return run_["id"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True, help="Account to set the demo up in")
    run(parser.parse_args().email)
