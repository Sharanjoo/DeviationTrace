# DeviationTrace

Automated cross-checking of manufacturer deviation records and SOPs against
QMSR (21 CFR Part 820) / ISO 13485:2016 / cGMP (21 CFR Part 211) requirements,
producing an evidence-linked gap report. See `DeviationTrace — Base System
PRD` for the full product spec.

**This repo currently implements Milestones 1–2 of 4**: the data model,
Postgres schema, FastAPI skeleton, a starter regulatory clause library
(deviation-handling and CAPA clauses only), and real document ingestion —
PDF/Word/text extraction, rule-based section splitting for SOPs and deviation
reports, and a keyword-based process-area detector. The cross-check matching
engine and the full UI screens are not yet implemented — see "What's stubbed"
below.

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

## What's real (Milestone 2)

- `POST /documents/{id}/process` runs a real synchronous pipeline: extracts
  text (`pdfplumber` for PDF, `python-docx` for Word, plain read for `.txt`),
  splits it into `DocumentSection` rows using a rule-based heading matcher
  (`backend/app/core/parsing/sections.py`), and runs a keyword-scored
  process-area detector (`backend/app/core/parsing/classify.py`) stored as
  `detected_process_area` for comparison against the user's own tag — it does
  not override it. Failures set `status="failed"` with `processing_error`
  populated instead of a 500.
- Section extraction only has a heading vocabulary for `sop` and `deviation`
  document types; `batch_record` uploads fall back to a single
  "Full Document" section (extraction for it is explicitly deferred per the
  PRD).

## What's stubbed (by design, for later milestones)

- `GET /findings` and the findings dashboard have no real data — the
  cross-check matching engine that produces findings is Milestone 3.
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
