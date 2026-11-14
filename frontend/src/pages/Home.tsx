import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { ProgressBar, type StatusDef } from "../components/CheckResults";
import { useOnboarding } from "../context/OnboardingContext";
import { countBy } from "../countBy";
import { downloadRunReport, formatRunDate, readiness, type SimulationRunSummary } from "../simulationRuns";

interface ChecklistItem {
  department: string;
  is_custom: boolean;
  is_excluded: boolean;
}
interface VendorDocument {
  id: string;
  status: string;
}
interface VendorFinding {
  document: { id: string };
  status: string;
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
  const [vendorDocs, setVendorDocs] = useState<VendorDocument[]>([]);
  const [vendorFindings, setVendorFindings] = useState<VendorFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.get<SimulationRunSummary[]>("/audit-simulation/runs"),
      api.get<ChecklistItem[]>("/audit-simulation/checklist"),
      api.get<VendorDocument[]>("/documents?type=vendor_audit_report"),
      api.get<VendorFinding[]>("/vendor-audit/findings"),
    ])
      .then(([r, c, d, f]) => {
        setRuns(r);
        setChecklist(c);
        setVendorDocs(d);
        setVendorFindings(f);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load your dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const latest = runs[0] ?? null;

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await api.post<{ run_id: string }>("/audit-simulation/run");
      navigate(`/audit-simulation/runs/${result.run_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
      setRunning(false);
    }
  };

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

  const vendorCounts = countBy(vendorFindings, (f) => f.status);
  const vendorTotal = vendorFindings.length;
  const vendorChecked = new Set(vendorFindings.map((f) => f.document.id)).size;

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
                    <button type="button" onClick={handleRun} disabled={running} className="btn-primary px-4 py-2 text-sm">
                      {running ? "Running..." : "Run new simulation"}
                    </button>
                    {latest && (
                      <Link to="/audit-simulation" className="btn-secondary px-4 py-2 text-sm">
                        Current results
                      </Link>
                    )}
                  </>
                }
              >
                {latest ? (
                  <div>
                    <div className="flex items-end justify-between gap-4">
                      <Stat label={`Readiness at ${latest.run_code}`} value={<span className="text-gradient">{readiness(latest)}%</span>} />
                      <p className="text-xs" style={muted}>
                        {formatRunDate(latest.created_at)}
                      </p>
                    </div>
                    <ProgressBar
                      statuses={SIM_STATUSES}
                      counts={{ missing: latest.missing, incomplete: latest.incomplete, satisfied: latest.satisfied }}
                      className="mt-3"
                    />
                    <p className="mt-2 text-xs" style={muted}>
                      {latest.missing} missing · {latest.incomplete} incomplete · {latest.satisfied} satisfied
                    </p>
                  </div>
                ) : (
                  <p className="text-sm" style={muted}>
                    No runs yet. Upload department reports first for meaningful results.
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
                    Edit checklist
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
                description="A PDF of the latest simulation run, ready to share with QA leadership or your SME."
                actions={
                  <button
                    type="button"
                    onClick={handleDownload}
                    disabled={!latest || downloading}
                    className="btn-primary px-4 py-2 text-sm"
                  >
                    {downloading ? "Preparing PDF..." : latest ? `Download ${latest.run_code} report` : "Run a simulation first"}
                  </button>
                }
              >
                {latest ? (
                  <p className="text-sm" style={muted}>
                    From <strong style={{ color: "var(--text)" }}>{latest.run_code}</strong>, run{" "}
                    {formatRunDate(latest.created_at)}. {latest.total} requirements, grouped by department.
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
                title="Run history"
                description="Review the latest run and every previous one by its ID, each with its own findings and report."
                actions={
                  <Link to="/audit-simulation/runs" className="btn-secondary px-4 py-2 text-sm">
                    View all runs{runs.length > 0 && ` (${runs.length})`}
                  </Link>
                }
              >
                {runs.length > 0 ? (
                  <ul className="divide-y text-sm" style={{ borderColor: "var(--glass-border)" }}>
                    {runs.slice(0, 3).map((run) => (
                      <li key={run.id} style={{ borderColor: "var(--glass-border)" }}>
                        <Link
                          to={`/audit-simulation/runs/${run.id}`}
                          className="flex items-center justify-between gap-4 py-2 hover:underline"
                        >
                          <span className="font-semibold" style={{ color: "var(--brand-blue-text)" }}>
                            {run.run_code}
                          </span>
                          <span className="flex-1 truncate" style={muted}>
                            {formatRunDate(run.created_at)}
                          </span>
                          <span className="font-semibold">{readiness(run)}%</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm" style={muted}>
                    Each run is saved here with an ID like SIM-0001.
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
              description="Check each supplier's audit report against the standards for its vendor category."
              actions={
                <>
                  <Link to="/vendor-audit" className="btn-primary px-4 py-2 text-sm">
                    Open vendor audit
                  </Link>
                  <Link to="/upload" className="btn-secondary px-4 py-2 text-sm">
                    Upload vendor report
                  </Link>
                </>
              }
            >
              <div className="grid gap-6 sm:grid-cols-[repeat(3,minmax(0,1fr))_2fr] sm:items-end">
                <Stat label="Reports uploaded" value={vendorDocs.length} />
                <Stat label="Cross-checked" value={`${vendorChecked} / ${vendorDocs.length}`} />
                <Stat
                  label="Standards met"
                  value={vendorTotal ? `${Math.round(((vendorCounts.satisfied ?? 0) / vendorTotal) * 100)}%` : "—"}
                />
                <div>
                  <ProgressBar statuses={VENDOR_STATUSES} counts={vendorCounts} />
                  <p className="mt-2 text-xs" style={muted}>
                    {vendorTotal
                      ? `${vendorCounts.missing ?? 0} missing · ${vendorCounts.partial ?? 0} partial · ${vendorCounts.satisfied ?? 0} satisfied`
                      : "No cross-checks run yet"}
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
