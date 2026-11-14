import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { CheckHeader, EmptyState, ProgressBar, type StatusDef } from "../components/CheckResults";
import { downloadRunReport, formatRunDate, readiness, type SimulationRunSummary } from "../simulationRuns";

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

  const previousReadiness = (index: number) => (runs[index + 1] ? readiness(runs[index + 1]) : null);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <CheckHeader
        eyebrow="Internal audit simulation"
        title="Run history"
        description="Every simulation run is kept with its own ID, findings and report, so you can see how readiness changed over time."
        action={
          <Link to="/audit-simulation" className="btn-secondary px-4 py-2 text-sm">
            Current results
          </Link>
        }
      />

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {loading && <p style={{ color: "var(--text-muted)" }}>Loading runs...</p>}

      {!loading && runs.length === 0 && (
        <EmptyState
          title="No runs yet"
          body="Run the internal audit simulation and each run will be saved here with an ID like SIM-0001."
          actionLabel="Go to simulation"
          actionTo="/audit-simulation"
        />
      )}

      {runs.length > 0 && (
        <div className="card overflow-hidden">
          <div
            className="hidden grid-cols-[110px_1fr_110px_1.4fr_auto] gap-4 border-b px-5 py-3 text-xs font-semibold uppercase tracking-wider md:grid"
            style={{ borderColor: "var(--glass-border)", color: "var(--text-muted)" }}
          >
            <span>Run</span>
            <span>Date</span>
            <span>Readiness</span>
            <span>Results</span>
            <span className="text-right">Report</span>
          </div>
          <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
            {runs.map((run, index) => {
              const score = readiness(run);
              const prev = previousReadiness(index);
              const delta = prev === null ? null : score - prev;
              return (
                <li
                  key={run.id}
                  className="grid grid-cols-2 items-center gap-x-4 gap-y-2 px-5 py-4 md:grid-cols-[110px_1fr_110px_1.4fr_auto]"
                  style={{ borderColor: "var(--glass-border)" }}
                >
                  <Link
                    to={`/audit-simulation/runs/${run.id}`}
                    className="font-semibold hover:underline"
                    style={{ color: "var(--brand-blue-text)" }}
                  >
                    {run.run_code}
                    {index === 0 && (
                      <span
                        className="ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
                        style={{ background: "var(--tint-blue)" }}
                      >
                        Latest
                      </span>
                    )}
                  </Link>
                  <span className="text-right text-sm md:text-left" style={{ color: "var(--text-muted)" }}>
                    {formatRunDate(run.created_at)}
                  </span>
                  <span className="font-semibold">
                    {score}%
                    {delta !== null && delta !== 0 && (
                      <span
                        className="ml-1.5 text-xs"
                        style={{ color: delta > 0 ? "var(--severity-resolved)" : "var(--severity-critical)" }}
                      >
                        {delta > 0 ? "▲" : "▼"}
                        {Math.abs(delta)}
                      </span>
                    )}
                  </span>
                  <div className="col-span-2 md:col-span-1">
                    <ProgressBar
                      statuses={STATUSES}
                      counts={{ missing: run.missing, incomplete: run.incomplete, satisfied: run.satisfied }}
                    />
                    <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                      {run.missing} missing · {run.incomplete} incomplete · {run.satisfied} satisfied
                    </p>
                  </div>
                  <div className="col-span-2 flex gap-2 md:col-span-1 md:justify-end">
                    <Link to={`/audit-simulation/runs/${run.id}`} className="btn-secondary px-3 py-1.5 text-xs">
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
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
