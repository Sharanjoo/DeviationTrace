import { useEffect, useMemo, useState } from "react";
import { GlassPanel, SeverityChip } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";

interface AuditChecklistFindingOut {
  id: string;
  checklist_item: {
    department: string;
    item_name: string;
    citation: string;
    requirement_text: string;
  };
  matched_document: { id: string; title: string } | null;
  status: "missing" | "incomplete" | "satisfied";
  severity: "critical" | "major" | "resolved";
  explanation: string;
  evaluated_at: string;
}

interface AuditSimulationRunResult {
  missing: number;
  incomplete: number;
  satisfied: number;
}

const DEPARTMENTS = [
  { value: "qc", label: "QC" },
  { value: "qa", label: "QA" },
  { value: "utilities", label: "Utilities" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "engineering", label: "Engineering" },
];

const STATUSES = ["missing", "incomplete", "satisfied"];

export function AuditSimulation() {
  const [findings, setFindings] = useState<AuditChecklistFindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<AuditSimulationRunResult | null>(null);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const loadFindings = () => {
    setLoading(true);
    api
      .get<AuditChecklistFindingOut[]>("/audit-simulation/findings")
      .then(setFindings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load findings."))
      .finally(() => setLoading(false));
  };

  useEffect(loadFindings, []);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await api.post<AuditSimulationRunResult>("/audit-simulation/run");
      setLastRun(result);
      loadFindings();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
    } finally {
      setRunning(false);
    }
  };

  const filtered = useMemo(
    () =>
      findings.filter(
        (f) =>
          (!departmentFilter || f.checklist_item.department === departmentFilter) &&
          (!statusFilter || f.status === statusFilter),
      ),
    [findings, departmentFilter, statusFilter],
  );

  const grouped = useMemo(() => {
    const groups = new Map<string, AuditChecklistFindingOut[]>();
    for (const finding of filtered) {
      const key = finding.checklist_item.department;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(finding);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  const departmentLabel = (value: string) => DEPARTMENTS.find((d) => d.value === value)?.label ?? value;

  const summarize = (rows: AuditChecklistFindingOut[]) => {
    const counts = { missing: 0, incomplete: 0, satisfied: 0 };
    for (const row of rows) counts[row.status] += 1;
    return STATUSES.filter((s) => counts[s as keyof typeof counts] > 0)
      .map((s) => `${counts[s as keyof typeof counts]} ${s}`)
      .join(", ");
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="flex items-end justify-between gap-4">
        <h1 className="text-3xl font-bold">Internal audit simulation</h1>
        <button
          type="button"
          onClick={handleRun}
          disabled={running}
          className="btn-primary px-4 py-2 text-sm"
        >
          {running ? "Running..." : "Run simulation"}
        </button>
      </div>

      {lastRun && (
        <GlassPanel>
          <p className="text-sm">
            Last run: {lastRun.missing} missing, {lastRun.incomplete} incomplete, {lastRun.satisfied} satisfied.
          </p>
        </GlassPanel>
      )}

      <div className="flex gap-4 text-sm">
        <select
          className="rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
        >
          <option value="">All departments</option>
          {DEPARTMENTS.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading findings...</p>}
      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {!loading && !error && findings.length === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>
            No results yet. Upload department reports from the Upload page, then click "Run simulation".
          </p>
        </GlassPanel>
      )}
      {!loading && !error && findings.length > 0 && filtered.length === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>No findings match these filters.</p>
        </GlassPanel>
      )}

      {grouped.map(([department, rows]) => (
        <div key={department} className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            {departmentLabel(department)} — {summarize(rows)}
          </h2>
          {rows.map((finding) => (
            <GlassPanel key={finding.id} className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {finding.checklist_item.citation}
                </div>
                <div className="mt-1 font-medium">
                  {finding.checklist_item.item_name}
                  <span className="ml-2 text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                    {finding.status}
                  </span>
                </div>
                <p className="mt-2 text-sm">{finding.explanation}</p>
                {finding.matched_document && (
                  <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                    Matched: {finding.matched_document.title}
                  </div>
                )}
              </div>
              <SeverityChip severity={finding.severity} />
            </GlassPanel>
          ))}
        </div>
      ))}
    </div>
  );
}
