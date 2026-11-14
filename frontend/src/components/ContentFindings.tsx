import { useState } from "react";
import { api, ApiError } from "../api/client";
import {
  DEPARTMENT_NAMES,
  REVIEW_LABELS,
  type ContentFinding,
  type ReviewDecision,
  type SimulationRunDetail,
} from "../simulationRuns";
import { StatusIcon, StatusPill, type StatusDef } from "./CheckResults";

const muted = { color: "var(--text-muted)" };
const SEVERITY: Record<string, StatusDef> = {
  critical: { value: "critical", label: "Not addressed", tone: "bad" },
  major: { value: "major", label: "Partly addressed", tone: "warn" },
};
const DECISIONS: ReviewDecision[] = ["confirmed", "false_positive", "needs_sme"];

function displayTitle(filename: string): string {
  return filename.replace(/\.(docx|pdf|txt)$/i, "").replace(/_/g, " ");
}

/** Content half of an internal audit run: requirements that the run's SOPs
 * and deviation reports don't (fully) address, grouped by document, each
 * with a review decision. */
export function ContentFindings({
  run,
  onChange,
}: {
  run: SimulationRunDetail;
  onChange: (finding: ContentFinding) => void;
}) {
  const [showDismissed, setShowDismissed] = useState(false);

  const byDocument = new Map<string, ContentFinding[]>();
  for (const f of run.content_findings) {
    if (!byDocument.has(f.document_title)) byDocument.set(f.document_title, []);
    byDocument.get(f.document_title)!.push(f);
  }
  const dismissed = run.content_findings.filter((f) => f.decision === "false_positive").length;
  const checked = run.content_documents_checked ?? 0;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Content check</p>
          <h2 className="mt-1 text-2xl font-bold">SOPs and deviation reports</h2>
          <p className="mt-1 max-w-3xl text-sm" style={muted}>
            {checked === 0
              ? "No SOPs or deviation reports were in scope for this audit, so nothing was content-checked. Add them in step 2 of a new simulation, choosing “SOP” or “Deviation report”."
              : `${checked} document${checked === 1 ? "" : "s"} read and checked against the regulatory requirements for their topic. Matching is keyword-based, so review each gap: confirm it, or dismiss it as a false positive.`}
          </p>
        </div>
        {checked > 0 && (
          <div className="flex gap-3 text-sm">
            <Count label="Not addressed" value={run.content_critical} tone="bad" />
            <Count label="Partly addressed" value={run.content_major} tone="warn" />
            <Count label="To review" value={run.content_unreviewed} />
          </div>
        )}
      </div>

      {checked > 0 && run.content_findings.length === 0 && (
        <div className="card flex items-center gap-3 p-5 text-sm">
          <StatusIcon tone="good" size={22} />
          Every content-checked document addresses all of its requirements.
        </div>
      )}

      {dismissed > 0 && (
        <label className="flex items-center gap-2 text-sm" style={muted}>
          <input type="checkbox" checked={showDismissed} onChange={(e) => setShowDismissed(e.target.checked)} />
          Show {dismissed} dismissed as false positive{dismissed === 1 ? "" : "s"}
        </label>
      )}

      {[...byDocument.entries()].map(([title, findings]) => {
        const visible = findings.filter((f) => showDismissed || f.decision !== "false_positive");
        const open = findings.filter((f) => f.decision !== "false_positive").length;
        const first = findings[0];
        return (
          <section key={title} className="card overflow-hidden">
            <header className="border-b px-5 py-4" style={{ borderColor: "var(--glass-border)" }}>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-semibold [overflow-wrap:anywhere]">{displayTitle(title)}</h3>
                <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase" style={{ background: "var(--tint-violet)", color: "#6d28d9" }}>
                  {first.document_type === "sop" ? "SOP" : "Deviation report"}
                </span>
              </div>
              <p className="mt-0.5 text-sm" style={muted}>
                {DEPARTMENT_NAMES[first.department] ?? first.department} · {open} open gap{open === 1 ? "" : "s"}
                {open !== findings.length && ` · ${findings.length - open} dismissed`}
              </p>
            </header>
            <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
              {visible.map((f) => (
                <FindingRow key={f.id} runId={run.id} finding={f} onChange={onChange} />
              ))}
              {visible.length === 0 && (
                <li className="px-5 py-4 text-sm" style={muted}>
                  All gaps for this document were dismissed as false positives.
                </li>
              )}
            </ul>
          </section>
        );
      })}
    </section>
  );
}

function Count({ label, value, tone }: { label: string; value: number; tone?: "bad" | "warn" }) {
  const color = tone === "bad" ? "var(--severity-critical)" : tone === "warn" ? "var(--severity-major)" : "var(--text)";
  return (
    <div className="card px-4 py-2 text-center">
      <p className="text-xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="text-xs" style={muted}>
        {label}
      </p>
    </div>
  );
}

function FindingRow({
  runId,
  finding,
  onChange,
}: {
  runId: string;
  finding: ContentFinding;
  onChange: (finding: ContentFinding) => void;
}) {
  const [showRequirement, setShowRequirement] = useState(false);
  const [note, setNote] = useState(finding.decision_note ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const severity = SEVERITY[finding.severity];
  const dismissed = finding.decision === "false_positive";

  const decide = async (decision: ReviewDecision | null) => {
    setSaving(true);
    setError(null);
    try {
      onChange(
        await api.post<ContentFinding>(`/audit-simulation/runs/${runId}/content-findings/${finding.id}/review`, {
          decision,
          note,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save the review.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <li className={`flex gap-4 px-5 py-4 ${dismissed ? "opacity-60" : ""}`} style={{ borderColor: "var(--glass-border)" }}>
      <StatusIcon tone={severity.tone} size={22} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <p className="font-semibold">{finding.requirement_title}</p>
          <StatusPill status={severity} />
        </div>
        <p className="mt-0.5 text-xs font-medium" style={{ color: "var(--brand-blue-text)" }}>
          {finding.citation}
          {finding.section_heading && finding.section_heading !== "Unclassified" && (
            <span style={muted}> · expected under “{finding.section_heading}”</span>
          )}
        </p>
        <p className="mt-1.5 text-sm" style={muted}>
          {finding.explanation}{" "}
          <button type="button" className="underline" onClick={() => setShowRequirement(!showRequirement)}>
            {showRequirement ? "Hide" : "What's required?"}
          </button>
        </p>
        {showRequirement && (
          <p className="mt-2 rounded-lg border px-3 py-2 text-sm" style={{ borderColor: "var(--glass-border)", background: "#f8fafc" }}>
            {finding.requirement_text}
          </p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium" style={muted}>
            Review:
          </span>
          {DECISIONS.map((d) => {
            const active = finding.decision === d;
            return (
              <button
                key={d}
                type="button"
                aria-pressed={active}
                disabled={saving}
                onClick={() => decide(active ? null : d)}
                className="rounded-full border px-3 py-1 text-xs font-medium"
                style={
                  active
                    ? { background: "var(--tint-blue)", borderColor: "var(--brand-blue)", color: "var(--brand-blue-text)" }
                    : { background: "#fff", borderColor: "var(--glass-border)", color: "#4b5563" }
                }
              >
                {REVIEW_LABELS[d]}
              </button>
            );
          })}
          <input
            className="min-w-[180px] flex-1 rounded-lg border px-2.5 py-1 text-xs"
            style={{ borderColor: "var(--glass-border)", color: "var(--text)" }}
            placeholder="Note (optional, saved with the decision)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        {finding.decision && finding.decided_by && (
          <p className="mt-1.5 text-xs" style={muted}>
            {REVIEW_LABELS[finding.decision]} by {finding.decided_by}
            {finding.decided_at && ` on ${new Date(finding.decided_at).toLocaleDateString()}`}
            {finding.decision_note && ` · “${finding.decision_note}”`}
          </p>
        )}
        {error && (
          <p className="mt-1.5 text-xs" style={{ color: "var(--severity-critical)" }}>
            {error}
          </p>
        )}
      </div>
    </li>
  );
}
