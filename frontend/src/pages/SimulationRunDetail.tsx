import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { CheckHeader, FilterChips, GroupCard, ResultRow, StatCards, type StatusDef } from "../components/CheckResults";
import { countBy } from "../countBy";
import { downloadRunReport, formatRunDate, type SimulationRunDetail as RunDetail } from "../simulationRuns";

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

/** One saved simulation run: its frozen findings and its PDF report. */
export function SimulationRunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    api
      .get<RunDetail>(`/audit-simulation/runs/${runId}`)
      .then(setRun)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load this run."));
  }, [runId]);

  const inDepartment = useMemo(
    () => (run?.items ?? []).filter((i) => !departmentFilter || i.department === departmentFilter),
    [run, departmentFilter],
  );
  const counts = useMemo(() => countBy(inDepartment, (i) => i.status), [inDepartment]);
  const groups = useMemo(
    () =>
      DEPARTMENTS.map((d) => ({ department: d, all: inDepartment.filter((i) => i.department === d.value) }))
        .filter((g) => g.all.length > 0)
        .map((g) => ({ ...g, shown: g.all.filter((i) => !statusFilter || i.status === statusFilter) }))
        .filter((g) => g.shown.length > 0),
    [inDepartment, statusFilter],
  );
  const departmentCounts = countBy(run?.items ?? [], (i) => i.department);

  const handleDownload = async () => {
    if (!run) return;
    setDownloading(true);
    setError(null);
    try {
      await downloadRunReport(run);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download report.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <Link to="/audit-simulation/runs" className="text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
        ← All runs
      </Link>

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {!run && !error && <p style={{ color: "var(--text-muted)" }}>Loading run...</p>}

      {run && (
        <>
          <CheckHeader
            eyebrow="Internal audit simulation"
            title={`Run ${run.run_code}`}
            description={`Run on ${formatRunDate(run.created_at)}. These results are a saved snapshot: later checklist edits or new uploads don't change them.`}
            action={
              <button type="button" onClick={handleDownload} disabled={downloading} className="btn-primary px-5 py-2.5 text-sm">
                {downloading ? "Preparing PDF..." : "Download PDF report"}
              </button>
            }
          />

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
              Nothing {STATUS_BY_VALUE[statusFilter]?.label.toLowerCase()} in this run.{" "}
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
              counts={countBy(all, (i) => i.status)}
            >
              {shown.map((i) => (
                <ResultRow
                  key={i.id}
                  status={STATUS_BY_VALUE[i.status]}
                  title={i.item_name}
                  citation={i.citation}
                  explanation={i.explanation}
                  footnote={i.matched_document_title ? <>Matched document: {i.matched_document_title}</> : undefined}
                />
              ))}
            </GroupCard>
          ))}
        </>
      )}
    </div>
  );
}
