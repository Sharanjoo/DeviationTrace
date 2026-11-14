import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import {
  CheckHeader,
  EmptyState,
  FilterChips,
  GroupCard,
  ResultRow,
  StatCards,
  type StatusDef,
} from "../components/CheckResults";
import { countBy } from "../countBy";

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

const DEPARTMENTS = [
  { value: "qc", label: "QC", name: "Quality Control" },
  { value: "qa", label: "QA", name: "Quality Assurance" },
  { value: "utilities", label: "Utilities", name: "Utilities" },
  { value: "manufacturing", label: "Manufacturing", name: "Manufacturing" },
  { value: "engineering", label: "Engineering", name: "Engineering" },
];

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "incomplete", label: "Incomplete", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const STATUS_BY_VALUE = Object.fromEntries(STATUSES.map((s) => [s.value, s]));

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function AuditSimulation() {
  const [findings, setFindings] = useState<AuditChecklistFindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [savedRun, setSavedRun] = useState<{ run_id: string; run_code: string } | null>(null);

  const loadFindings = () => {
    setLoading(true);
    return api
      .get<AuditChecklistFindingOut[]>("/audit-simulation/findings")
      .then(setFindings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load findings."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadFindings();
  }, []);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      setSavedRun(await api.post<{ run_id: string; run_code: string }>("/audit-simulation/run"));
      await loadFindings();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
    } finally {
      setRunning(false);
    }
  };

  // Stats follow the department filter; the status filter only narrows rows.
  const inDepartment = useMemo(
    () => findings.filter((f) => !departmentFilter || f.checklist_item.department === departmentFilter),
    [findings, departmentFilter],
  );
  const counts = useMemo(() => countBy(inDepartment, (f) => f.status), [inDepartment]);

  const groups = useMemo(
    () =>
      DEPARTMENTS.map((d) => ({
        department: d,
        all: inDepartment.filter((f) => f.checklist_item.department === d.value),
      }))
        .filter((g) => g.all.length > 0)
        .map((g) => ({ ...g, shown: g.all.filter((f) => !statusFilter || f.status === statusFilter) }))
        .filter((g) => g.shown.length > 0),
    [inDepartment, statusFilter],
  );

  const lastRun = findings.reduce<string | null>(
    (latest, f) => (!latest || f.evaluated_at > latest ? f.evaluated_at : latest),
    null,
  );
  const departmentCounts = countBy(findings, (f) => f.checklist_item.department);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <CheckHeader
        eyebrow="Verification check"
        title="Internal audit simulation"
        description="Checks that every department's required records exist and are complete, the way an internal auditor working through ISO 13485 §8.2.4 would."
        meta={
          lastRun ? (
            <>
              Last run {formatWhen(lastRun)} · against your{" "}
              <Link to="/org-checklist" className="underline">
                department checklist
              </Link>{" "}
              ·{" "}
              <Link to="/audit-simulation/runs" className="underline">
                Run history
              </Link>
            </>
          ) : undefined
        }
        action={
          findings.length > 0 && (
            <button type="button" onClick={handleRun} disabled={running} className="btn-primary px-5 py-2.5 text-sm">
              {running ? "Running..." : "Run simulation again"}
            </button>
          )
        }
      />

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {savedRun && (
        <div className="card flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
          <p>
            Saved as <strong>{savedRun.run_code}</strong>. It stays in your run history with its own report.
          </p>
          <Link to={`/audit-simulation/runs/${savedRun.run_id}`} className="btn-secondary px-3 py-1.5 text-xs">
            View {savedRun.run_code}
          </Link>
        </div>
      )}
      {loading && findings.length === 0 && <p style={{ color: "var(--text-muted)" }}>Loading results...</p>}

      {!loading && findings.length === 0 && (
        <EmptyState
          title="No simulation run yet"
          body="Upload each department's reports (as type “Department report”), then run the simulation to see what an auditor would find missing or incomplete."
          actionLabel={running ? "Running..." : "Run simulation"}
          onAction={handleRun}
        />
      )}

      {findings.length > 0 && (
        <>
          <StatCards scoreLabel="Audit readiness" statuses={STATUSES} counts={counts} active={statusFilter} onSelect={setStatusFilter} />

          <FilterChips
            allLabel="All departments"
            value={departmentFilter}
            onChange={setDepartmentFilter}
            options={DEPARTMENTS.filter((d) => departmentCounts[d.value]).map((d) => ({
              value: d.value,
              label: d.label,
              count: departmentCounts[d.value],
            }))}
          />

          {groups.length === 0 && (
            <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
              Nothing {STATUS_BY_VALUE[statusFilter]?.label.toLowerCase()} here.{" "}
              <button type="button" className="underline" onClick={() => setStatusFilter("")}>
                Show all statuses
              </button>
            </div>
          )}

          {groups.map(({ department, all, shown }) => (
            <GroupCard
              key={department.value}
              title={department.name}
              subtitle={`${all.length} required record${all.length === 1 ? "" : "s"}`}
              statuses={STATUSES}
              counts={countBy(all, (f) => f.status)}
            >
              {shown.map((f) => (
                <ResultRow
                  key={f.id}
                  status={STATUS_BY_VALUE[f.status]}
                  title={f.checklist_item.item_name}
                  citation={f.checklist_item.citation}
                  explanation={f.explanation}
                  footnote={f.matched_document ? <>Matched document: {f.matched_document.title}</> : undefined}
                />
              ))}
            </GroupCard>
          ))}
        </>
      )}
    </div>
  );
}
