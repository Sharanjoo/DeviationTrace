import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { AiInteractionDetail, AiInteractionSummary } from "../ai";

const muted = { color: "var(--text-muted)" };
const STATUS_STYLE: Record<AiInteractionSummary["status"], { label: string; style: React.CSSProperties }> = {
  success: { label: "Completed", style: { background: "var(--severity-resolved-tint)", color: "var(--severity-resolved)" } },
  refused: { label: "Declined by model", style: { background: "var(--severity-major-tint)", color: "var(--severity-major)" } },
  error: { label: "Failed", style: { background: "var(--severity-critical-tint)", color: "var(--severity-critical)" } },
};

/** Admin-only record of every request sent to an AI model: who sent it,
 * which document and sections, where it went, and the exact text sent and
 * received. */
export function AiActivityLog() {
  const [entries, setEntries] = useState<AiInteractionSummary[] | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AiInteractionSummary[]>("/org/ai-log")
      .then(setEntries)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load the AI activity log."));
  }, []);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <Link to="/company" className="text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
          ← Company profile
        </Link>
        <p className="eyebrow mt-3">AI assistance</p>
        <h1 className="mt-2 text-3xl font-bold">AI activity log</h1>
        <p className="mt-2" style={muted}>
          Every request sent to an AI model, including ones that failed, with exactly what was sent and what came back.
          Only admins can see this.
        </p>
      </div>

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {entries && entries.length === 0 && (
        <div className="card p-6 text-sm" style={muted}>
          Nothing has been sent to an AI model yet.
        </div>
      )}

      {entries && entries.length > 0 && (
        <ul className="flex flex-col gap-3">
          {entries.map((e) => (
            <li key={e.id} className="card overflow-hidden">
              <button
                type="button"
                onClick={() => setOpenId(openId === e.id ? null : e.id)}
                className="flex w-full flex-wrap items-start justify-between gap-3 px-5 py-4 text-left"
              >
                <div className="min-w-0">
                  <p className="font-semibold [overflow-wrap:anywhere]">{e.document_title ?? "Untitled document"}</p>
                  <p className="mt-0.5 text-sm" style={muted}>
                    {new Date(e.created_at).toLocaleString()} · {e.user_name} · {e.sections_sent.length} section
                    {e.sections_sent.length === 1 ? "" : "s"} sent{e.redacted ? `, ${e.redaction_count} identifiers removed` : ", not redacted"}
                  </p>
                  <p className="mt-0.5 text-xs" style={muted}>
                    {e.provider} · {e.model_used ?? e.model_requested}
                    {e.fallback_used && " (fallback model)"}
                    {e.input_tokens != null && ` · ${e.input_tokens.toLocaleString()} in / ${(e.output_tokens ?? 0).toLocaleString()} out tokens`}
                    {e.duration_ms != null && ` · ${(e.duration_ms / 1000).toFixed(1)}s`}
                  </p>
                </div>
                <span className="rounded-full px-2.5 py-1 text-xs font-semibold" style={STATUS_STYLE[e.status].style}>
                  {STATUS_STYLE[e.status].label}
                </span>
              </button>
              {openId === e.id && <InteractionDetail id={e.id} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function InteractionDetail({ id }: { id: string }) {
  const [detail, setDetail] = useState<AiInteractionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AiInteractionDetail>(`/org/ai-log/${id}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load this entry."));
  }, [id]);

  if (error) return <p className="px-5 pb-4 text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>;
  if (!detail) return <p className="px-5 pb-4 text-sm" style={muted}>Loading…</p>;

  return (
    <div className="flex flex-col gap-3 border-t px-5 py-4 text-sm" style={{ borderColor: "var(--glass-border)" }}>
      {detail.error && <p style={{ color: "var(--severity-critical)" }}>{detail.error}</p>}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider" style={muted}>
          Sections sent
        </p>
        <p className="mt-1">
          {detail.sections_sent.map((s) => `${s.heading} (${s.characters.toLocaleString()} characters)`).join(", ") || "None"}
        </p>
      </div>
      <Block label="Instructions sent to the model" text={detail.system_prompt} />
      <Block label="Requirements and document text sent" text={detail.user_prompt} />
      <Block label="Response received" text={detail.response_text ?? "No response."} />
      {detail.request_id && (
        <p className="text-xs" style={muted}>
          Provider request ID: {detail.request_id}
        </p>
      )}
    </div>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wider" style={muted}>
        {label}
      </p>
      <pre className="mt-1 max-h-72 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">{text}</pre>
    </div>
  );
}
