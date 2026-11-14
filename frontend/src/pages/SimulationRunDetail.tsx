import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { AuditDetailsCard } from "../components/AuditDetailsCard";
import { AuditDocumentsStep } from "../components/AuditDocumentsStep";
import { AuditStepper } from "../components/AuditStepper";
import { ContentFindings } from "../components/ContentFindings";
import { CheckHeader, FilterChips, GroupCard, ResultRow, StatCards, type StatusDef } from "../components/CheckResults";
import { countBy } from "../countBy";
import {
  DEPARTMENTS,
  downloadRunReport,
  formatRunDate,
  runDate,
  type ContentFinding,
  type SimulationRunDetail as RunDetail,
} from "../simulationRuns";

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "incomplete", label: "Incomplete", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const STATUS_BY_VALUE = Object.fromEntries(STATUSES.map((s) => [s.value, s]));

/** One simulation run. A draft shows step 2 (upload documents, then run);
 * a completed run shows its frozen findings and PDF report. */
export function SimulationRunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  // True right after executing here, to keep showing the step indicator.
  const [justRan, setJustRan] = useState(false);

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

  // Apply a review decision locally, keeping the open-gap counts in step.
  const updateContentFinding = (updated: ContentFinding) =>
    setRun((prev) => {
      if (!prev) return prev;
      const content_findings = prev.content_findings.map((f) => (f.id === updated.id ? updated : f));
      const open = content_findings.filter((f) => f.decision !== "false_positive");
      return {
        ...prev,
        content_findings,
        content_critical: open.filter((f) => f.severity === "critical").length,
        content_major: open.filter((f) => f.severity === "major").length,
        content_unreviewed: content_findings.filter((f) => !f.decision).length,
      };
    });

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

  if (run?.status === "draft") {
    return (
      <AuditDocumentsStep
        run={run}
        onExecuted={(done) => {
          setRun(done);
          setJustRan(true);
          window.scrollTo({ top: 0 });
        }}
      />
    );
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      {justRan && run && <AuditStepper current={2} runCode={run.run_code} />}
      <Link to="/audit-simulation/runs" className="text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
        ← All audits
      </Link>

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {!run && !error && <p style={{ color: "var(--text-muted)" }}>Loading run...</p>}

      {run && (
        <>
          <CheckHeader
            eyebrow="Internal audit simulation"
            title={run.title ? `${run.run_code} · ${run.title}` : `Run ${run.run_code}`}
            description={`Run on ${formatRunDate(runDate(run))}. These results are a saved snapshot: later checklist edits or new uploads don't change them.`}
            action={
              <button type="button" onClick={handleDownload} disabled={downloading} className="btn-primary px-5 py-2.5 text-sm">
                {downloading ? "Preparing PDF..." : "Download PDF report"}
              </button>
            }
          />

          <AuditDetailsCard run={run} />

          <div>
            <p className="eyebrow">Records check</p>
            <h2 className="mt-1 text-2xl font-bold">Required records</h2>
            <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
              Does each department have the records an auditor will ask for, and are they complete?
            </p>
          </div>

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

          <div className="mt-4 border-t pt-8" style={{ borderColor: "var(--glass-border)" }}>
            <ContentFindings run={run} onChange={updateContentFinding} />
          </div>
        </>
      )}
    </div>
  );
}
