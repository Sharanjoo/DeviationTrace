import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { applyAuditFilters, QUICK_RUN, useAuditFilters } from "../auditFilters";
import { AuditFilterPanel } from "../components/AuditFilters";
import { CheckHeader, EmptyState, ProgressBar, type StatusDef } from "../components/CheckResults";
import {
  AUDIT_TYPE_LABELS,
  DEPARTMENT_NAMES,
  DEPARTMENTS,
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

const muted = { color: "var(--text-muted)" };

/** Pick a completed audit and download its PDF report. Filters mirror the
 * details entered when starting a simulation (see AuditFilters). */
export function AuditReports() {
  const [runs, setRuns] = useState<SimulationRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const filters = useAuditFilters();

  useEffect(() => {
    api
      .get<SimulationRunSummary[]>("/audit-simulation/runs")
      .then((all) => setRuns(all.filter((r) => r.status === "completed")))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load audits."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = applyAuditFilters(runs, filters);

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

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <Link to="/" className="text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
        ← Home
      </Link>
      <CheckHeader
        eyebrow="Internal audit simulation"
        title="Generate report"
        description="Find the audit you need and download its PDF report. Each report is built from that audit's saved results, so it reads the same whenever you download it."
      />

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {loading && <p style={muted}>Loading audits...</p>}

      {!loading && runs.length === 0 && (
        <EmptyState
          title="No completed audits yet"
          body="Reports are generated from a completed audit simulation. Start one, upload documents and run it."
          actionLabel="Start a simulation"
          actionTo="/audit-simulation/new"
        />
      )}

      {runs.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <AuditFilterPanel filters={filters} runs={runs} />

          {/* Results */}
          <section className="flex flex-col gap-3">
            <p className="text-sm" style={muted}>
              {filtered.length} of {runs.length} completed audit{runs.length === 1 ? "" : "s"}
            </p>

            {filtered.length === 0 && (
              <div className="card p-6 text-sm" style={muted}>
                No audits match these filters.{" "}
                <button type="button" className="underline" onClick={filters.clear}>
                  Clear filters
                </button>
              </div>
            )}

            {filtered.map((run) => (
              <article key={run.id} className="card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold" style={{ color: "var(--brand-blue-text)" }}>
                      {run.run_code}
                    </p>
                    <h3 className="text-lg font-semibold [overflow-wrap:anywhere]">{run.title ?? QUICK_RUN}</h3>
                    <p className="mt-0.5 text-xs" style={muted}>
                      {[
                        run.audit_type && AUDIT_TYPE_LABELS[run.audit_type],
                        run.lead_name && `Lead: ${run.lead_name} (${run.lead_employee_id})`,
                        `Run ${formatRunDate(runDate(run))}`,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Link to={`/audit-simulation/runs/${run.id}`} className="btn-secondary px-3 py-2 text-sm">
                      View
                    </Link>
                    <button
                      type="button"
                      onClick={() => handleDownload(run)}
                      disabled={downloadingId === run.id}
                      className="btn-primary px-4 py-2 text-sm"
                    >
                      {downloadingId === run.id ? "Preparing PDF..." : "Download PDF"}
                    </button>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
                  <p className="text-2xl font-bold text-gradient">{readiness(run)}%</p>
                  <div className="min-w-[200px] flex-1">
                    <ProgressBar statuses={STATUSES} counts={runCounts(run)} />
                    <p className="mt-1 text-xs" style={muted}>
                      {run.missing} missing · {run.incomplete} incomplete · {run.satisfied} satisfied
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(run.departments ?? DEPARTMENTS.map((d) => d.value)).map((d) => (
                      <span key={d} className="rounded-md border px-2 py-0.5 text-[11px]" style={{ borderColor: "var(--glass-border)", ...muted }}>
                        {DEPARTMENT_NAMES[d] ?? d}
                      </span>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
