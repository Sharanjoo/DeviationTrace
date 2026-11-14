import { api } from "./api/client";

/** Shared types, labels and helpers for internal audit simulation runs. */

export const AUDIT_TYPES = [
  { value: "internal_audit", label: "Internal audit (ISO 13485 §8.2.4)" },
  { value: "mock_fda_inspection", label: "Mock FDA inspection (QMSR)" },
  { value: "certification_readiness", label: "Certification / surveillance readiness" },
  { value: "customer_audit_prep", label: "Customer or partner audit preparation" },
  { value: "for_cause", label: "For-cause audit" },
];
export const AUDIT_TYPE_LABELS: Record<string, string> = Object.fromEntries(AUDIT_TYPES.map((t) => [t.value, t.label]));

export const DEPARTMENTS = [
  { value: "qc", label: "QC", name: "Quality Control" },
  { value: "qa", label: "QA", name: "Quality Assurance" },
  { value: "utilities", label: "Utilities", name: "Utilities" },
  { value: "manufacturing", label: "Manufacturing", name: "Manufacturing" },
  { value: "engineering", label: "Engineering", name: "Engineering" },
];
export const DEPARTMENT_NAMES: Record<string, string> = Object.fromEntries(DEPARTMENTS.map((d) => [d.value, d.name]));

export interface DepartmentContact {
  department: string;
  name: string;
  employee_id: string;
}

export interface AuditDetails {
  title: string;
  audit_type: string;
  planned_date: string | null;
  lead_name: string;
  lead_employee_id: string;
  lead_title: string | null;
  lead_email: string | null;
  objective: string | null;
  departments: string[];
  department_contacts: DepartmentContact[];
}

export interface SimulationRunSummary {
  id: string;
  run_number: number;
  run_code: string;
  status: "draft" | "completed";
  created_at: string;
  completed_at: string | null;
  missing: number | null;
  incomplete: number | null;
  satisfied: number | null;
  total: number;
  // Audit details; null on quick runs made without them.
  title: string | null;
  audit_type: string | null;
  planned_date: string | null;
  lead_name: string | null;
  lead_employee_id: string | null;
  lead_title: string | null;
  lead_email: string | null;
  objective: string | null;
  departments: string[] | null;
  department_contacts: DepartmentContact[] | null;
  // Content check of SOPs and deviation reports
  content_documents_checked: number | null;
  content_critical: number;
  content_major: number;
  content_unreviewed: number;
}

export type ReviewDecision = "confirmed" | "false_positive" | "needs_sme";
export const REVIEW_LABELS: Record<ReviewDecision, string> = {
  confirmed: "Confirmed gap",
  false_positive: "False positive",
  needs_sme: "Needs SME",
};

export interface ContentFinding {
  id: string;
  department: string;
  document_title: string;
  document_type: "sop" | "deviation";
  citation: string;
  requirement_title: string;
  requirement_text: string;
  section_heading: string | null;
  status: "missing" | "partial";
  severity: "critical" | "major";
  explanation: string;
  decision: ReviewDecision | null;
  decision_note: string | null;
  decided_by: string | null;
  decided_at: string | null;
}

export interface SimulationRunItem {
  id: string;
  department: string;
  item_name: string;
  citation: string;
  status: "missing" | "incomplete" | "satisfied";
  severity: "critical" | "major" | "resolved";
  explanation: string;
  matched_document_title: string | null;
}

export interface SimulationRunDetail extends SimulationRunSummary {
  items: SimulationRunItem[];
  content_findings: ContentFinding[];
}

export function readiness(run: Pick<SimulationRunSummary, "satisfied" | "total">): number {
  return run.total ? Math.round(((run.satisfied ?? 0) / run.total) * 100) : 0;
}

export function runCounts(run: SimulationRunSummary): Record<string, number> {
  return { missing: run.missing ?? 0, incomplete: run.incomplete ?? 0, satisfied: run.satisfied ?? 0 };
}

/** When the run's results were produced (falls back to creation time). */
export function runDate(run: SimulationRunSummary): string {
  return run.completed_at ?? run.created_at;
}

export function formatRunDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatPlannedDate(isoDate: string): string {
  // A plain date (no time zone): build it locally so it doesn't shift a day.
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** Download a run's PDF report (the API needs the auth header, so this
 * fetches a blob rather than linking to the URL directly). */
export async function downloadRunReport(run: Pick<SimulationRunSummary, "id" | "run_code">): Promise<void> {
  const blob = await api.downloadBlob(`/audit-simulation/runs/${run.id}/report`);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `deviationtrace-${run.run_code}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}
