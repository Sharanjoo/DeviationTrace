# DeviationTrace

Automated cross-checking of manufacturer deviation records and SOPs against
QMSR (21 CFR Part 820) / ISO 13485:2016 / cGMP (21 CFR Part 211) requirements,
producing an evidence-linked gap report. See `DeviationTrace — Base System
PRD` for the full product spec.

**This repo currently implements Milestone 1 of 4**: the data model, Postgres
schema, FastAPI skeleton, and a starter regulatory clause library
(deviation-handling and CAPA clauses only). Document parsing, the cross-check
matching engine, and the full UI screens are not yet implemented — see
"What's stubbed" below.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for local Postgres)

## Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# from the repo root
docker compose up -d

cd backend
copy ..\.env.example ..\.env   # edit if needed
alembic upgrade head
python -m app.seed.load_clauses
uvicorn app.main:app --reload
```

API docs at <http://localhost:8000/docs>.

Run tests (needs Postgres up, migrated, and seeded first):

```powershell
cd backend
pytest
```

## Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open <http://localhost:5173>.

## What's stubbed (by design, for Milestone 1)

- `POST /documents/{id}/process` sets status to `queued` but does not run any
  real classify/extract/cross-check pipeline (Milestone 2/3).
- `GET /findings` and the findings dashboard have no real data — the matching
  engine that produces findings doesn't exist yet.
- `GET /reports/{org_id}/export` returns `501 Not Implemented`.
- The five frontend pages (Upload, Processing, Dashboard, Finding Detail,
  Report Export) are glassmorphism-styled shells with placeholder content —
  not wired to real upload/processing/triage flows yet (Milestone 4).
- The regulatory clause library (`backend/app/seed/data/*.yaml`) is an
  **illustrative draft** written for scaffolding purposes. It has not been
  reviewed by a regulatory SME and must not be used for real audit-readiness
  decisions until validated.

## Data model

Six PRD entities (`Organization`, `Document`, `DocumentSection`,
`RegulatoryClause`, `Finding`, `TriageDecision`) plus a `User` entity added to
back email/password auth and `TriageDecision.user_id`. See
`backend/alembic/versions/0001_initial_schema.py` for the schema and
`backend/app/models/` for the ORM definitions.
