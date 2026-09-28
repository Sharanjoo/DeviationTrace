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
export, plus a review queue and synthetic demo documents for SME sessions (see
"SME review walkthrough"). See "What's stubbed" for the deliberate scope cuts
that remain (real audit-readiness use needs SME review of the clause library
first).

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

## What's real (Phase 1 — Internal Audit Simulation)

Separate from the base system above: models a company's department
structure (QC, QA, Utilities, Manufacturing, Engineering) and checks
whether each department's required documents/reports exist and are
complete, per a fixed internal-audit checklist — an *existence/completeness*
check, not a content clause-match.

- Upload accepts a new `type="report"` and an optional `department` form
  field (`backend/app/api/routes/documents.py`); these documents use
  `process_area="general"` as a placeholder, since no `RegulatoryClause`
  targets it and the existing content-matching engine naturally produces no
  findings for them.
- `backend/app/core/audit_simulation/rule_based.py`'s
  `RuleBasedAuditSimulationEngine` matches each `AuditChecklistItem` against
  candidate documents in its department by title keyword (`match_phrases`),
  then applies a shallow completeness check (processed, and at least one
  section with >=400 characters of real content — enough to tell a stub
  title page from an actual report).
- `POST /audit-simulation/run` re-evaluates every checklist item for the
  org and upserts `AuditChecklistFinding` rows in place (never
  delete-and-recreate, same lesson as the base system's reprocess-FK bug).
  `GET /audit-simulation/findings?department=&status=` lists them.
- The checklist library (`backend/app/seed/data/checklist/*.yaml`, loaded
  via `python -m app.seed.load_checklist`) is, like the regulatory clause
  library, an **illustrative draft** — 3 items per department, not yet
  reviewed by an SME.
- No frontend yet — this phase is backend-only for now (mirrors how the
  base system itself was verified via pytest/curl before Milestone 4's UI
  existed). Nine synthetic department documents in `demo_documents/`
  (generated by `backend/app/seed/department_demo_documents.py`) exercise
  all three outcomes (`missing`/`incomplete`/`satisfied`) across all 5
  departments; see `tests/test_audit_simulation.py` for the exact expected
  mix.

## What's real (Module 2 — Vendor Audit Cross-Check)

Separate from the base system and Phase 1 above: checks a single uploaded
vendor audit report's own *content* against a small standards library, per
vendor/material category — confirming the vendor did what they claimed, not
just that a report exists. Built as its own parallel stack (not a reuse of
the base system's `RegulatoryClause`/`MatchingEngine`/`Finding`), mirroring
how Phase 1 was built standalone, so the four verification modules stay
independently selectable.

- Upload accepts a new `type="vendor_audit_report"` and an optional
  `vendor_category` form field (`backend/app/api/routes/documents.py`), a
  fixed vocabulary of 5 categories (`raw_material_supplier`,
  `contract_manufacturer`, `calibration_test_service`,
  `sterilization_service`, `packaging_component_supplier`). Like Phase 1's
  `department` reports, these use `process_area="general"` as a placeholder.
- `backend/app/core/vendor_audit/rule_based.py`'s `RuleBasedVendorAuditEngine`
  checks the document's extracted content against every `VendorStandard` for
  its `vendor_category`, using the same casefolded match-phrase technique as
  the base `MatchingEngine` — but unlike it, full phrase coverage still
  produces a row (`status="satisfied"`), not silence, so an SME can see what
  the vendor's report did claim, not only where it fell short.
- `POST /vendor-audit/{document_id}/run` re-evaluates one document (after
  `POST /documents/{id}/process` has produced its sections) and upserts
  `VendorAuditFinding` rows in place; `GET /vendor-audit/findings?vendor_category=&status=`
  lists them. Trigger is per-document and explicit, not an upload
  side-effect — mirrors `POST /audit-simulation/run` as its own action.
- The standards library (`backend/app/seed/data/vendor_standards/*.yaml`, 3
  standards per category, loaded via `python -m app.seed.load_vendor_standards`)
  is, like every other library in this repo, an **illustrative draft** not
  yet reviewed by an SME.
- No frontend yet — backend-only for now, same sequencing as Phase 1. Three
  synthetic vendor audit report documents in `demo_documents/` (generated by
  `backend/app/seed/vendor_audit_demo_documents.py`, one each for
  `raw_material_supplier`, `contract_manufacturer`, and
  `sterilization_service`) exercise all three outcomes
  (`missing`/`partial`/`satisfied`) within a single document; see
  `tests/test_vendor_audit.py` for the exact expected mix.

## SME review walkthrough

Five fictional documents in `demo_documents/` are tuned to give a subject-matter
expert a realistic mix to triage (20 findings: 10 critical, 10 major). Each one
says "synthetic" in its title block. They are generated by
`backend/app/seed/demo_documents.py`; rerun it only if you change the wording
(`cd backend && python -m app.seed.demo_documents`), and
`tests/test_demo_documents.py` fails if the committed files drift from the
generator or stop producing the intended findings.

Upload each file on the Upload page with the type and process area below:

| File | Type | Process area | Findings |
|---|---|---|---|
| `SOP-QA-014_Control_of_Nonconforming_Product.docx` | SOP | deviation_handling | 1 missing, 1 partial |
| `DEV-2026-0417_Stability_Chamber_Temperature_Excursion.docx` | Deviation | deviation_handling | 2 partial |
| `DEV-2026-0433_Label_Reconciliation_Discrepancy.docx` | Deviation | deviation_handling | 7 missing, 2 partial (thin report, mostly real gaps) |
| `SOP-QA-021_Corrective_and_Preventive_Action.docx` | SOP | capa | 1 partial |
| `DEV-2026-0451_Filling_Line_Stopper_Feed_Jams.docx` | Deviation | capa | 2 missing, 4 partial |

Then open **Review** in the nav. The queue lists pending findings critical-first
with a progress bar and per-decision filters; **Start reviewing** opens the
first one, and after each decision **Next pending finding** moves on. Decisions
and notes persist and can be changed later.

Several findings are deliberate false positives, where the wording satisfies
the requirement but not the curated phrase, so the SME can mark them "False
positive" and the rule-based limits show up as evidence: the `followup` /
`follow-up` spelling on `211.192` (SOP-QA-014), "no advisory notice required" on
`8.3.4` (DEV-2026-0417), "verify" but not "validate" on `820.100(a)(3)`
(SOP-QA-021), and the paraphrased `820.100(a)(6)` and `211.100(b)` passages in
DEV-2026-0451.

## What's stubbed (deliberate scope cuts, not gaps)

- The review queue has no analyst/SME roles, no triage history or audit trail
  (only the latest decision is kept), and triage decisions are not yet shown in
  the PDF report.
- SOP findings cite the document's title block ("Unclassified") as their
  source passage, because each clause's `expected_heading` uses deviation-style
  headings that SOP headings never match.
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
- Phase 1 (Internal Audit Simulation) has no frontend, and its checklist
  library is an equally illustrative draft (see above) — both deliberate
  scope cuts for this pass, not gaps discovered late.
- Module 2 (Vendor Audit Cross-Check) has no frontend either, and its
  standards library is an equally illustrative draft (see above) — same
  deliberate scope cuts as Phase 1, not gaps discovered late. Manufacturer
  Record Completeness and Material Certification Check (the other two
  planned verification modules) are on hold per SME guidance until Phase 1
  and Module 2 are both built and SME-validated.

## Data model

Six PRD entities (`Organization`, `Document`, `DocumentSection`,
`RegulatoryClause`, `Finding`, `TriageDecision`) plus a `User` entity added to
back email/password auth and `TriageDecision.user_id`. See
`backend/alembic/versions/0001_initial_schema.py` for the schema and
`backend/app/models/` for the ORM definitions. Phase 1 added
`AuditChecklistItem` and `AuditChecklistFinding`, plus a `department` column
on `Document` — see `backend/alembic/versions/0004_add_audit_simulation.py`.
Module 2 added `VendorStandard` and `VendorAuditFinding`, plus a
`vendor_category` column on `Document` — see
`backend/alembic/versions/0005_add_vendor_audit.py`.
