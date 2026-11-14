import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { GlassPanel, SeverityChip, TriageChip } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { TRIAGE_LABELS, type TriageDecisionValue } from "../triage";

interface FindingOut {
  id: string;
  document: { id: string; title: string; type: string };
  clause: { regulation: string; clause_number: string };
  status: string;
  severity: "critical" | "major" | "minor";
  explanation: string;
  triage_decision: { decision: TriageDecisionValue } | null;
}

type QueueFilter = "pending" | TriageDecisionValue | "all";

const FILTERS: { value: QueueFilter; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: TRIAGE_LABELS.confirmed },
  { value: "false_positive", label: TRIAGE_LABELS.false_positive },
  { value: "needs_sme", label: TRIAGE_LABELS.needs_sme },
  { value: "all", label: "All" },
];

function matchesFilter(finding: FindingOut, filter: QueueFilter): boolean {
  if (filter === "all") return true;
  if (filter === "pending") return finding.triage_decision === null;
  return finding.triage_decision?.decision === filter;
}

export function Review() {
  const [findings, setFindings] = useState<FindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<QueueFilter>("pending");

  useEffect(() => {
    api
      .get<FindingOut[]>("/findings")
      .then(setFindings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load findings."))
      .finally(() => setLoading(false));
  }, []);

  const counts = useMemo(() => {
    const tally: Record<QueueFilter, number> = {
      pending: 0,
      confirmed: 0,
      false_positive: 0,
      needs_sme: 0,
      all: findings.length,
    };
    for (const finding of findings) {
      tally[finding.triage_decision?.decision ?? "pending"] += 1;
    }
    return tally;
  }, [findings]);

  const visible = useMemo(() => findings.filter((f) => matchesFilter(f, filter)), [findings, filter]);
  const firstPending = findings.find((f) => f.triage_decision === null);
  const triaged = counts.all - counts.pending;
  const percent = counts.all === 0 ? 0 : Math.round((triaged / counts.all) * 100);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="flex items-end justify-between gap-4">
        <h1 className="text-3xl font-bold">Review queue</h1>
        {firstPending && (
          <Link
            to={`/findings/${firstPending.id}`}
            className="btn-primary px-4 py-2 text-sm"
          >
            Start reviewing
          </Link>
        )}
      </div>

      {!loading && !error && counts.all > 0 && (
        <GlassPanel>
          <div className="flex items-baseline justify-between text-sm">
            <span className="font-medium">
              {triaged} of {counts.all} triaged
            </span>
            <span style={{ color: "var(--text-muted)" }}>{percent}%</span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full"
            style={{ background: "var(--glass-border)" }}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={counts.all}
            aria-valuenow={triaged}
          >
            <div className="h-full" style={{ width: `${percent}%`, background: "var(--severity-resolved)" }} />
          </div>
        </GlassPanel>
      )}

      <div className="flex flex-wrap gap-2 text-sm">
        {FILTERS.map((option) => {
          const active = filter === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => setFilter(option.value)}
              className={`rounded-full border px-3 py-1 ${active ? "font-semibold" : ""}`}
              style={{
                borderColor: "var(--glass-border)",
                background: active ? "var(--surface-bg)" : "transparent",
                color: active ? "var(--surface-text)" : "inherit",
              }}
            >
              {option.label} ({counts[option.value]})
            </button>
          );
        })}
      </div>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading findings...</p>}
      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {!loading && !error && counts.all === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>
            No findings yet. <Link to="/upload" className="underline">Upload and process a document</Link> to start a review.
          </p>
        </GlassPanel>
      )}
      {!loading && !error && counts.all > 0 && visible.length === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>
            {filter === "pending" ? "All findings have been reviewed." : "No findings in this category."}
          </p>
        </GlassPanel>
      )}

      {visible.map((finding) => (
        <Link key={finding.id} to={`/findings/${finding.id}`}>
          <GlassPanel className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                {finding.document.title}
              </div>
              <div className="mt-1 font-medium">
                {finding.clause.regulation.toUpperCase()} {finding.clause.clause_number}
                <span className="ml-2 text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                  {finding.status}
                </span>
              </div>
              <p className="mt-2 text-sm">{finding.explanation}</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <SeverityChip severity={finding.severity} />
              <TriageChip decision={finding.triage_decision?.decision} />
            </div>
          </GlassPanel>
        </Link>
      ))}
    </div>
  );
}
