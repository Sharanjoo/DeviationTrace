# DeviationTrace

Automated cross-checking of manufacturer deviation records and SOPs against
QMSR (21 CFR Part 820) / ISO 13485:2016 / cGMP (21 CFR Part 211) requirements,
producing an evidence-linked gap report. See `DeviationTrace — Base System
PRD` for the full product spec.

**This repo currently implements all four PRD milestones of the base
system**: the data model, Postgres schema, FastAPI skeleton, a starter
regulatory clause library (deviation-handling and CAPA clauses only), real
document ingestion (PDF/Word/text extraction, rule-based section splitting, a
keyword-based process-area detector), a rule-based cross-check engine that
generates real `Finding` rows, and a frontend wired end-to-end to all of it —
real auth, upload, processing, findings dashboard, triage, and PDF report
export. See "What's stubbed" for the deliberate scope cuts that remain (real
audit-readiness use needs SME review of the clause library first).

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

## What's real (Milestone 3)

- After section extraction, `POST /documents/{id}/process` runs
  `RuleBasedMatchingEngine` (`backend/app/core/matching/rule_based.py`)
  against every `RegulatoryClause` applicable to the document's own
  `(type, process_area)`, using each clause's curated `match_phrases` — a
  clause with all its phrases present is fully addressed (no finding); zero
  phrases found is `status="missing"`/`severity="critical"`; some-but-not-all
  is `status="partial"`/`severity="major"`. `GET /findings` now returns real,
  cited findings.
- Reprocessing a document upserts findings by clause rather than
  delete-and-recreate, so a `TriageDecision` a QA user already recorded is
  never orphaned or silently dropped.
- The matcher never produces `"contradicted"` findings (SOP vs. deviation
  report disagreeing) — that needs real cross-document comparison, which is
  explicitly out of scope for this rule-based v1 (see the PRD's own
  rule-based-vs-LLM-assisted open question).

## What's real (Milestone 4)

- Real auth in the frontend (`src/context/AuthContext.tsx`, `src/pages/Login.tsx`):
  register an org or log in, JWT held in `localStorage`, all pages except
  `/login` gated behind `RequireAuth`.
- Upload → Processing → Dashboard → Finding Detail → Report Export is a real,
  wired flow — no placeholder data anywhere. Processing polls
  `GET /documents/{id}/status`; the Dashboard groups real findings by
  document with working severity/status filters; Finding Detail fetches the
  new `GET /findings/{id}` endpoint and submits real triage decisions; Report
  Export shows on-screen counts and downloads a real PDF from
  `GET /reports/{org_id}/export` (generated with `fpdf2` — counts by severity
  and process area, then a per-finding list with citations).
- Verified with a full headless-Chromium walkthrough (register → upload a
  real SOP → watch it process → see real findings → triage one → download and
  read back the PDF) — not just that the pages render.
- Two real bugs were caught and fixed via that walkthrough, not by the
  pre-existing test suite: (1) a React StrictMode dev double-invoke in
  `Processing.tsx` was silently dropping the first `/process` result — fixed
  by removing an "only run once" ref guard that raced against effect cleanup,
  safe now that reprocessing is idempotent; (2) that same double-invoke
  exposed a real concurrency bug where two simultaneous `/process` calls for
  one document could both read "no existing findings" and both insert,
  doubling every finding — fixed with a `SELECT ... FOR UPDATE` row lock in
  `documents.py`'s `process_document`, with a regression test
  (`test_concurrent_process_calls_do_not_duplicate_findings`) covering it.

## What's stubbed (deliberate scope cuts, not gaps)

- `process_area` in the Upload form is restricted to `deviation_handling` and
  `capa` — the only two the seeded clause library covers.
- Finding Detail is its own route, not the PRD's "side panel over the
  dashboard" — a layout choice, not a functional gap.
- The regulatory clause library (`backend/app/seed/data/*.yaml`) is an
  **illustrative draft** written for scaffolding purposes. It has not been
  reviewed by a regulatory SME and must not be used for real audit-readiness
  decisions until validated.
- The matcher never produces `"contradicted"` findings (SOP vs. deviation
  report disagreeing) — that needs real cross-document comparison, out of
  scope for this rule-based v1.

## Data model

Six PRD entities (`Organization`, `Document`, `DocumentSection`,
`RegulatoryClause`, `Finding`, `TriageDecision`) plus a `User` entity added to
back email/password auth and `TriageDecision.user_id`. See
`backend/alembic/versions/0001_initial_schema.py` for the schema and
`backend/app/models/` for the ORM definitions.
