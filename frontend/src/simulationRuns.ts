import { api } from "./api/client";

/** Shared types and helpers for internal audit simulation run history. */

export interface SimulationRunSummary {
  id: string;
  run_number: number;
  run_code: string;
  created_at: string;
  missing: number;
  incomplete: number;
  satisfied: number;
  total: number;
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
}

export function readiness(run: Pick<SimulationRunSummary, "satisfied" | "total">): number {
  return run.total ? Math.round((run.satisfied / run.total) * 100) : 0;
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
