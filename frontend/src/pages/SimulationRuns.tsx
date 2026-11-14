import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { applyAuditFilters, useAuditFilters } from "../auditFilters";
import { AuditFilterPanel } from "../components/AuditFilters";
import { CheckHeader, EmptyState, ProgressBar, type StatusDef } from "../components/CheckResults";
import {
  downloadRunReport,
  formatRunDate,
  readiness,
  runCounts,
  runDate,
  type SimulationRunSummary,
} from "../simulationRuns";

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "incomplete", label: "Incomplete", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];

/** Every internal audit simulation run for the org, newest first. */
export function SimulationRuns() {
  const [runs, setRuns] = useState<SimulationRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<SimulationRunSummary[]>("/audit-simulation/runs")
      .then(setRuns)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load runs."))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (run: SimulationRunSummary) => {
    setDownloadingId(run.id);
    setError(null);
    try {
      await downloadRunReport(run);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download report.");
    } finally {
      setDownloadingId(null);
    }
  };

  // Change vs. the next older completed run with the same departments in
  // scope. Scores across different scopes aren't comparable, and drafts
  // have no score.
  const scopeKey = (r: SimulationRunSummary) => (r.departments ? [...r.departments].sort().join(",") : "all");
  // Compared against the full history, not just the filtered rows.
  const previousReadiness = (run: SimulationRunSummary) => {
    const index = runs.indexOf(run);
    const prev = runs.slice(index + 1).find((r) => r.status === "completed" && scopeKey(r) === scopeKey(run));
    return prev ? readiness(prev) : null;
  };
  const latestCompletedId = runs.find((r) => r.status === "completed")?.id;
  const filters = useAuditFilters();
  const filtered = applyAuditFilters(runs, filters);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <CheckHeader
        eyebrow="Internal audit simulation"
        title="All audits"
        description="Every audit simulation, by ID and name, with its own findings and report. Readiness changes are shown against the previous audit of the same departments."
        action={
          <Link to="/audit-simulation/new" className="btn-primary px-4 py-2 text-sm">
            New simulation
          </Link>
        }
      />

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {loading && <p style={{ color: "var(--text-muted)" }}>Loading runs...</p>}

      {!loading && runs.length === 0 && (
        <EmptyState
          title="No audits yet"
          body="Start an audit simulation and it will be saved here with an ID like SIM-0001 and the name you give it."
          actionLabel="Start a simulation"
          actionTo="/audit-simulation/new"
        />
      )}

      {runs.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <AuditFilterPanel filters={filters} runs={runs} showStatus />
          <section className="flex min-w-0 flex-col gap-3">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {filtered.length} of {runs.length} audit
              {runs.length === 1 ? "" : "s"}
            </p>
            {filtered.length === 0 && (
              <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
                No audits match these filters.{" "}
                <button type="button" className="underline" onClick={filters.clear}>
                  Clear filters
                </button>
              </div>
            )}
            {filtered.length > 0 && (
              <div className="card overflow-hidden">
                <div
                  className="hidden grid-cols-[130px_1fr_90px_1.2fr_auto] gap-4 border-b px-5 py-3 text-xs font-semibold uppercase tracking-wider md:grid"
                  style={{
                    borderColor: "var(--glass-border)",
                    color: "var(--text-muted)",
                  }}
                >
                  <span>Run</span>
                  <span>Audit</span>
                  <span>Readiness</span>
                  <span>Results</span>
                  <span className="text-right">Report</span>
                </div>
                <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
                  {filtered.map((run) => {
                    const isDraft = run.status === "draft";
                    const score = readiness(run);
                    const prev = isDraft ? null : previousReadiness(run);
                    const delta = prev === null ? null : score - prev;
                    return (
                      <li
                        key={run.id}
                        className="grid grid-cols-2 items-center gap-x-4 gap-y-2 px-5 py-4 md:grid-cols-[130px_1fr_90px_1.2fr_auto]"
                        style={{ borderColor: "var(--glass-border)" }}
                      >
                        <div className="min-w-0">
                          <Link
                            to={`/audit-simulation/runs/${run.id}`}
                            className="block whitespace-nowrap font-semibold hover:underline"
                            style={{ color: "var(--brand-blue-text)" }}
                          >
                            {run.run_code}
                          </Link>
                          {isDraft ? (
                            <span
                              className="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
                              style={{
                                background: "var(--severity-major-tint)",
                                color: "var(--severity-major)",
                              }}
                            >
                              Draft
                            </span>
                          ) : (
                            run.id === latestCompletedId && (
                              <span
                                className="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
                                style={{
                                  background: "var(--tint-blue)",
                                  color: "var(--brand-blue-text)",
                                }}
                              >
                                Latest
                              </span>
                            )
                          )}
                        </div>
                        <div className="min-w-0 text-right md:text-left">
                          <p className="truncate text-sm font-medium">{run.title ?? "Quick run (all departments)"}</p>
                          <p className="truncate text-xs" style={{ color: "var(--text-muted)" }}>
                            {formatRunDate(runDate(run))}
                            {run.lead_name && ` · ${run.lead_name} (${run.lead_employee_id})`}
                          </p>
                        </div>
                        <span className="font-semibold">
                          {isDraft ? (
                            <span className="text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                              Not run yet
                            </span>
                          ) : (
                            <>
                              {score}%
                              {delta !== null && delta !== 0 && (
                                <span
                                  className="ml-1.5 text-xs"
                                  style={{
                                    color: delta > 0 ? "var(--severity-resolved)" : "var(--severity-critical)",
                                  }}
                                >
                                  {delta > 0 ? "▲" : "▼"}
                                  {Math.abs(delta)}
                                </span>
                              )}
                            </>
                          )}
                        </span>
                        <div className="col-span-2 md:col-span-1">
                          {isDraft ? (
                            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                              Waiting for documents · {(run.departments ?? []).length || 5} department
                              {(run.departments ?? []).length === 1 ? "" : "s"} in scope
                            </p>
                          ) : (
                            <>
                              <ProgressBar statuses={STATUSES} counts={runCounts(run)} />
                              <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                                {run.missing} missing · {run.incomplete} incomplete · {run.satisfied} satisfied
                              {run.content_critical + run.content_major > 0 &&
                                ` · ${run.content_critical + run.content_major} content gap${run.content_critical + run.content_major === 1 ? "" : "s"}`}
                              </p>
                            </>
                          )}
                        </div>
                        <div className="col-span-2 flex gap-2 md:col-span-1 md:justify-end">
                          {isDraft ? (
                            <Link to={`/audit-simulation/runs/${run.id}`} className="btn-primary px-3 py-1.5 text-xs">
                              Continue
                            </Link>
                          ) : (
                            <>
                              <Link
                                to={`/audit-simulation/runs/${run.id}`}
                                className="btn-secondary px-3 py-1.5 text-xs"
                              >
                                View
                              </Link>
                              <button
                                type="button"
                                onClick={() => handleDownload(run)}
                                disabled={downloadingId === run.id}
                                className="btn-secondary px-3 py-1.5 text-xs"
                              >
                                {downloadingId === run.id ? "Preparing..." : "PDF"}
                              </button>
                            </>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
