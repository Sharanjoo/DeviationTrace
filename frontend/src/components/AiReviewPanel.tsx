import { useCallback, useState } from "react";
import { api, ApiError } from "../api/client";
import { VERDICT_LABELS, type AiAssessment, type AiPreview, type AiVerdict } from "../ai";
import type { ContentFinding } from "../simulationRuns";
import { StatusIcon } from "./CheckResults";

const muted = { color: "var(--text-muted)" };
const VERDICT_TONE: Record<AiVerdict, "good" | "warn" | "bad"> = {
  addressed: "good",
  partly_addressed: "warn",
  not_addressed: "bad",
};
const TONE_STYLE = {
  good: { background: "var(--severity-resolved-tint)", color: "var(--severity-resolved)" },
  warn: { background: "var(--severity-major-tint)", color: "var(--severity-major)" },
  bad: { background: "var(--severity-critical-tint)", color: "var(--severity-critical)" },
};

/** Optional AI review of one content-checked document in a run. The user
 * picks which sections to send and whether to remove identifiers, can see
 * exactly what will be sent, then sends it. Results sit next to the
 * rule-based result for each requirement; they don't replace it. */
export function AiReviewPanel({
  runId,
  documentId,
  ruleFindings,
  assessments,
  onReviewed,
}: {
  runId: string;
  documentId: string;
  ruleFindings: ContentFinding[];
  assessments: AiAssessment[];
  onReviewed: (assessments: AiAssessment[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<AiPreview | null>(null);
  const [selected, setSelected] = useState<string[] | null>(null);
  const [redact, setRedact] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const base = `/audit-simulation/runs/${runId}/documents/${documentId}`;

  const loadPreview = useCallback(
    async (sectionIds: string[] | null, redactValue: boolean | null) => {
      setLoading(true);
      setError(null);
      try {
        const next = await api.post<AiPreview>(`${base}/ai-preview`, { section_ids: sectionIds, redact: redactValue });
        setPreview(next);
        setSelected(next.selected_section_ids);
        setRedact(next.redact);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Couldn't prepare the AI review.");
      } finally {
        setLoading(false);
      }
    },
    [base],
  );

  const start = () => {
    setOpen(true);
    if (!preview) loadPreview(null, null);
  };

  const toggleSection = (id: string) => {
    if (!selected) return;
    const next = selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id];
    setSelected(next);
    if (next.length > 0) loadPreview(next, redact);
  };

  const send = async () => {
    if (!selected?.length) return;
    setSending(true);
    setError(null);
    try {
      const result = await api.post<{ assessments: AiAssessment[] }>(`${base}/ai-review`, {
        section_ids: selected,
        redact,
      });
      onReviewed(result.assessments);
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The AI review failed.");
    } finally {
      setSending(false);
    }
  };

  const sentCharacters = preview
    ? preview.sections.filter((s) => selected?.includes(s.id)).reduce((n, s) => n + s.characters, 0)
    : 0;
  const ruleResult = (title: string) => {
    const finding = ruleFindings.find((f) => f.requirement_title === title);
    if (!finding) return { label: "Addressed", tone: "good" as const };
    if (finding.decision === "false_positive") return { label: "Dismissed", tone: "good" as const };
    return finding.severity === "critical"
      ? { label: "Not addressed", tone: "bad" as const }
      : { label: "Partly addressed", tone: "warn" as const };
  };

  return (
    <div className="border-t px-5 py-4" style={{ borderColor: "var(--glass-border)", background: "#fbfaff" }}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">AI review</p>
          <p className="text-xs" style={muted}>
            {assessments.length
              ? `Last reviewed ${new Date(assessments[0].created_at).toLocaleString()}. Shown next to the rule-based result; review both.`
              : "Optional: ask an AI model to judge whether this document meets each requirement, with quoted evidence."}
          </p>
        </div>
        {!open && (
          <button type="button" onClick={start} className="btn-secondary px-3 py-1.5 text-xs">
            {assessments.length ? "Review again with AI" : "Review with AI"}
          </button>
        )}
      </div>

      {open && (
        <div className="mt-4 flex flex-col gap-3">
          {loading && !preview && <p className="text-sm" style={muted}>Preparing…</p>}
          {preview && selected && (
            <>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider" style={muted}>
                  1. Choose which sections to send
                </p>
                <ul className="mt-2 flex flex-col gap-1.5">
                  {preview.sections.map((s) => (
                    <li key={s.id}>
                      <label className="flex cursor-pointer items-start gap-2 rounded-lg border bg-white px-3 py-2 text-sm" style={{ borderColor: "var(--glass-border)" }}>
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 accent-blue-600"
                          checked={selected.includes(s.id)}
                          onChange={() => toggleSection(s.id)}
                        />
                        <span className="min-w-0">
                          <span className="font-medium">{s.heading}</span>{" "}
                          <span className="text-xs" style={muted}>
                            {s.characters.toLocaleString()} characters
                          </span>
                          <span className="block truncate text-xs" style={muted}>
                            {s.preview}
                          </span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-blue-600"
                  checked={!!redact}
                  onChange={(e) => {
                    setRedact(e.target.checked);
                    if (selected.length) loadPreview(selected, e.target.checked);
                  }}
                />
                2. Remove names, emails, phone numbers and employee IDs before sending
                {redact && preview.redaction_count > 0 && (
                  <span className="text-xs" style={muted}>
                    ({preview.redaction_count} replaced)
                  </span>
                )}
              </label>

              <details className="rounded-lg border bg-white px-3 py-2 text-sm" style={{ borderColor: "var(--glass-border)" }}>
                <summary className="cursor-pointer font-medium">3. See exactly what will be sent</summary>
                <p className="mt-2 text-xs" style={muted}>
                  Instructions to the model:
                </p>
                <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{preview.system_prompt}</pre>
                <p className="mt-2 text-xs" style={muted}>
                  Requirements and document text:
                </p>
                <pre className="mt-1 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{preview.user_prompt}</pre>
              </details>

              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-white px-3 py-2" style={{ borderColor: "var(--glass-border)" }}>
                <p className="text-xs" style={muted}>
                  Sending {selected.length} of {preview.sections.length} sections ({sentCharacters.toLocaleString()} characters) and{" "}
                  {preview.requirements.length} requirements to <strong>{preview.provider_label}</strong> ({preview.model}). This is
                  logged, including the exact text.
                </p>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setOpen(false)} className="btn-secondary px-3 py-1.5 text-xs">
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={send}
                    disabled={sending || loading || selected.length === 0}
                    className="btn-primary px-3 py-1.5 text-xs"
                  >
                    {sending ? "Reviewing… (can take a minute)" : "Send for AI review"}
                  </button>
                </div>
              </div>
            </>
          )}
          {error && <p className="text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>}
        </div>
      )}

      {assessments.length > 0 && !open && (
        <ul className="mt-3 flex flex-col gap-2">
          {assessments.map((a) => {
            const rule = ruleResult(a.requirement_title);
            const tone = VERDICT_TONE[a.verdict];
            const disagrees = (tone === "good") !== (rule.tone === "good");
            return (
              <li key={a.id} className="rounded-lg border bg-white px-3 py-2.5 text-sm" style={{ borderColor: disagrees ? "var(--brand-violet)" : "var(--glass-border)" }}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="font-semibold">
                    {a.requirement_title}{" "}
                    <span className="text-xs font-medium" style={{ color: "var(--brand-blue-text)" }}>
                      {a.citation}
                    </span>
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-semibold">
                    <span className="rounded-full px-2 py-0.5" style={TONE_STYLE[rule.tone]}>
                      Rules: {rule.label}
                    </span>
                    <span className="rounded-full px-2 py-0.5" style={TONE_STYLE[tone]}>
                      AI: {VERDICT_LABELS[a.verdict]}
                    </span>
                    {disagrees && (
                      <span className="rounded-full px-2 py-0.5" style={{ background: "var(--tint-violet)", color: "#6d28d9" }}>
                        Disagree: check this one
                      </span>
                    )}
                  </div>
                </div>
                <p className="mt-1 text-xs" style={muted}>
                  {a.reasoning}
                </p>
                {a.evidence && (
                  <p className="mt-1.5 flex items-start gap-1.5 text-xs">
                    <StatusIcon tone={a.evidence_verified ? "good" : "warn"} size={16} />
                    <span>
                      <span className="italic">“{a.evidence}”</span>{" "}
                      <span style={muted}>
                        {a.evidence_verified ? "(quote found in the text sent)" : "(quote not found in the text sent: verify it)"}
                      </span>
                    </span>
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
