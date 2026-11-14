import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { ProgressBar, type StatusDef } from "../components/CheckResults";
import { useOnboarding } from "../context/OnboardingContext";
import {
  downloadRunReport,
  formatRunDate,
  readiness,
  runCounts,
  runDate,
  type SimulationRunSummary,
} from "../simulationRuns";
import type { Vendor } from "../vendors";

interface ChecklistItem {
  department: string;
  is_custom: boolean;
  is_excluded: boolean;
}
const SIM_STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "incomplete", label: "Incomplete", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const VENDOR_STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "partial", label: "Partial", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];

const ICONS = {
  simulation: "M9 11l3 3L22 4M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11",
  checklist: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  report: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M12 18v-6M9 15l3 3 3-3",
  history: "M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8M3 3v5h5M12 7v5l4 2",
  vendor:
    "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75",
};

function Tile({
  icon,
  tint,
  color,
  step,
  title,
  description,
  children,
  actions,
  className = "",
}: {
  icon: string;
  tint: string;
  color: string;
  step?: string;
  title: string;
  description: string;
  children?: ReactNode;
  actions: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card flex flex-col p-6 ${className}`}>
      <div className="flex items-start gap-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl" style={{ background: tint }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d={icon} />
          </svg>
        </span>
        <div className="min-w-0">
          {step && (
            <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
              {step}
            </p>
          )}
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
            {description}
          </p>
        </div>
      </div>
      {children && <div className="mt-5 flex-1">{children}</div>}
      <div className="mt-5 flex flex-wrap gap-2">{actions}</div>
    </section>
  );
}

function Stat({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        {label}
      </p>
      <p className="mt-0.5 text-2xl font-bold" style={color ? { color } : undefined}>
        {value}
      </p>
    </div>
  );
}

/** Landing page after login: one block per thing you can do, in the order
 * you'd do them for an internal audit, then the vendor check on its own. */
export function Home() {
  const navigate = useNavigate();
  const { status } = useOnboarding();
  const [runs, setRuns] = useState<SimulationRunSummary[]>([]);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<SimulationRunSummary[]>("/audit-simulation/runs"),
      api.get<ChecklistItem[]>("/audit-simulation/checklist"),
      api.get<Vendor[]>("/vendors"),
    ])
      .then(([r, c, v]) => {
        setRuns(r);
        setChecklist(c);
        setVendors(v);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load your dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const completedRuns = runs.filter((r) => r.status === "completed");
  const latest = completedRuns[0] ?? null;
  // The newest unfinished audit (details entered, not yet run), if any.
  const draft = runs.find((r) => r.status === "draft") ?? null;

  // Quick download of the latest completed audit's report; any other audit
  // is picked on the Reports page.
  const handleDownload = async () => {
    if (!latest) return;
    setDownloading(true);
    setError(null);
    try {
      await downloadRunReport(latest);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download report.");
    } finally {
      setDownloading(false);
    }
  };

  const activeItems = checklist.filter((i) => !i.is_excluded);
  const departmentsCovered = new Set(activeItems.map((i) => i.department)).size;
  const customItems = checklist.filter((i) => i.is_custom).length;
  const excludedItems = checklist.filter((i) => i.is_excluded).length;

  // Vendor summary across each vendor's latest audit.
  const latestVendorAudits = vendors.flatMap((v) => (v.latest_audit ? [v.latest_audit] : []));
  const vendorCounts = {
    missing: latestVendorAudits.reduce((n, a) => n + a.missing, 0),
    partial: latestVendorAudits.reduce((n, a) => n + a.partial, 0),
    satisfied: latestVendorAudits.reduce((n, a) => n + a.satisfied, 0),
  };
  const vendorTotal = vendorCounts.missing + vendorCounts.partial + vendorCounts.satisfied;
  const vendorAuditCount = vendors.reduce((n, v) => n + v.audit_count, 0);

  const muted = { color: "var(--text-muted)" };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8">
      <div>
        <p className="eyebrow">Dashboard</p>
        <h1 className="mt-2 text-3xl font-bold">{status?.org_name ? `Welcome, ${status.org_name}` : "Welcome"}</h1>
        <p className="mt-2" style={muted}>
          Pick what you want to do. Everything for the internal audit is grouped together; the vendor audit is its own
          check below.
        </p>
      </div>

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {loading && <p style={muted}>Loading your dashboard...</p>}

      {!loading && (
        <>
          <section className="flex flex-col gap-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={muted}>
              Internal audit
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              <Tile
                icon={ICONS.simulation}
                tint="var(--tint-blue)"
                color="var(--brand-blue)"
                step="Run"
                title="Internal audit simulation"
                description="Check every department's required records against your checklist, the way an auditor would."
                actions={
                  <>
                    <button
                      type="button"
                      onClick={() => navigate("/audit-simulation/new")}
                      className="btn-primary px-4 py-2 text-sm"
                    >
                      Run new simulation
                    </button>
                    {draft && (
                      <Link to={`/audit-simulation/runs/${draft.id}`} className="btn-secondary px-4 py-2 text-sm">
                        Continue {draft.run_code} (draft)
                      </Link>
                    )}
                    {runs.length > 0 && (
                      <Link to="/audit-simulation/runs" className="btn-secondary px-4 py-2 text-sm">
                        All audits ({runs.length})
                      </Link>
                    )}
                  </>
                }
              >
                {latest ? (
                  <div>
                    <div className="flex items-end justify-between gap-4">
                      <Stat label="Latest readiness" value={<span className="text-gradient">{readiness(latest)}%</span>} />
                      <p className="min-w-0 text-right text-xs" style={muted}>
                        <span className="block truncate font-semibold" style={{ color: "var(--text)" }}>
                          {latest.run_code} · {latest.title ?? "Quick run"}
                        </span>
                        {formatRunDate(runDate(latest))}
                      </p>
                    </div>
                    <ProgressBar
                      statuses={SIM_STATUSES}
                      counts={runCounts(latest)}
                      className="mt-3"
                    />
                    <p className="mt-2 text-xs" style={muted}>
                      {latest.missing} missing · {latest.incomplete} incomplete · {latest.satisfied} satisfied
                    </p>
                  </div>
                ) : (
                  <p className="text-sm" style={muted}>
                    No runs yet. You'll enter the audit's details, upload each department's reports, then run it.
                  </p>
                )}
              </Tile>

              <Tile
                icon={ICONS.checklist}
                tint="var(--tint-violet)"
                color="var(--brand-violet)"
                step="Set up"
                title="Department checklist"
                description="The required records the simulation checks for. Turn items off or add your own."
                actions={
                  <Link to="/org-checklist" className="btn-secondary px-4 py-2 text-sm">
                    View checklist
                  </Link>
                }
              >
                <div className="grid grid-cols-3 gap-4">
                  <Stat label="Active items" value={activeItems.length} />
                  <Stat label="Departments" value={departmentsCovered} />
                  <Stat label="Custom / off" value={`${customItems} / ${excludedItems}`} />
                </div>
              </Tile>

              <Tile
                icon={ICONS.report}
                tint="var(--tint-blue)"
                color="var(--brand-blue)"
                step="Report"
                title="Generate report"
                description="A PDF of any completed audit, ready to share with QA leadership or your SME."
                actions={
                  <>
                    <button
                      type="button"
                      onClick={() => navigate("/audit-simulation/reports")}
                      disabled={!latest}
                      className="btn-primary px-4 py-2 text-sm"
                    >
                      {latest ? "Choose an audit" : "Run a simulation first"}
                    </button>
                    {latest && (
                      <button
                        type="button"
                        onClick={handleDownload}
                        disabled={downloading}
                        className="btn-secondary px-4 py-2 text-sm"
                      >
                        {downloading ? "Preparing PDF..." : `Latest (${latest.run_code})`}
                      </button>
                    )}
                  </>
                }
              >
                {latest ? (
                  <p className="text-sm" style={muted}>
                    {completedRuns.length} completed audit{completedRuns.length === 1 ? "" : "s"} to choose from. Filter
                    by name, type, lead auditor, departments or date, then download the one you need.
                  </p>
                ) : (
                  <p className="text-sm" style={muted}>
                    Reports are generated from a simulation run. Run one to enable this.
                  </p>
                )}
              </Tile>

              <Tile
                icon={ICONS.history}
                tint="var(--tint-violet)"
                color="var(--brand-violet)"
                step="Review"
                title="All audits"
                description="Every audit by its ID and name. Open one to see its findings and report."
                actions={
                  <Link to="/audit-simulation/runs" className="btn-secondary px-4 py-2 text-sm">
                    View all audits{runs.length > 0 && ` (${runs.length})`}
                  </Link>
                }
              >
                {runs.length > 0 ? (
                  <ul className="divide-y text-sm" style={{ borderColor: "var(--glass-border)" }}>
                    {runs.slice(0, 5).map((run) => (
                      <li key={run.id} style={{ borderColor: "var(--glass-border)" }}>
                        <Link
                          to={`/audit-simulation/runs/${run.id}`}
                          className="flex items-center gap-3 rounded-md py-2 hover:bg-slate-50"
                        >
                          <span className="w-[76px] shrink-0 font-semibold" style={{ color: "var(--brand-blue-text)" }}>
                            {run.run_code}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate font-medium">{run.title ?? "Quick run (all departments)"}</span>
                            <span className="block truncate text-xs" style={muted}>
                              {formatRunDate(runDate(run))}
                              {run.lead_name && ` · ${run.lead_name}`}
                            </span>
                          </span>
                          {run.status === "draft" ? (
                            <span
                              className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold"
                              style={{ background: "var(--severity-major-tint)", color: "var(--severity-major)" }}
                            >
                              Draft
                            </span>
                          ) : (
                            <span className="shrink-0 font-semibold">{readiness(run)}%</span>
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm" style={muted}>
                    Each audit is saved here with an ID like SIM-0001 and the name you give it.
                  </p>
                )}
              </Tile>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={muted}>
              Vendor audit
            </h2>
            <Tile
              icon={ICONS.vendor}
              tint="#fdf2f8"
              color="#db2777"
              title="Vendor audit cross-check"
              description="Your vendors and their audit history. Open a vendor to review previous audits or start a new one."
              actions={
                <Link to="/vendor-audit" className="btn-primary px-4 py-2 text-sm">
                  Open vendor audit
                </Link>
              }
            >
              <div className="grid gap-6 sm:grid-cols-[repeat(3,minmax(0,1fr))_2fr] sm:items-end">
                <Stat label="Vendors" value={vendors.length} />
                <Stat label="Audits" value={vendorAuditCount} />
                <Stat
                  label="Standards met (latest audits)"
                  value={vendorTotal ? `${Math.round((vendorCounts.satisfied / vendorTotal) * 100)}%` : "—"}
                />
                <div>
                  <ProgressBar statuses={VENDOR_STATUSES} counts={vendorCounts} />
                  <p className="mt-2 text-xs" style={muted}>
                    {vendorTotal
                      ? `${vendorCounts.missing} missing · ${vendorCounts.partial} partial · ${vendorCounts.satisfied} satisfied`
                      : vendors.length
                        ? "No audits yet"
                        : "No vendors added yet"}
                  </p>
                </div>
              </div>
            </Tile>
          </section>
        </>
      )}
    </div>
  );
}
