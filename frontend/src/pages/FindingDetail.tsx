import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { GlassPanel, SeverityChip } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { TRIAGE_LABELS, type TriageDecisionValue } from "../triage";

interface FindingOut {
  id: string;
  document: { id: string; title: string; type: string };
  section: { heading: string; text: string };
  clause: { regulation: string; clause_number: string; requirement_text: string };
  status: string;
  severity: "critical" | "major" | "minor";
  explanation: string;
  triage_decision: { decision: TriageDecisionValue; note: string | null } | null;
}

const DECISIONS = Object.entries(TRIAGE_LABELS) as [TriageDecisionValue, string][];

/** Keyed by id so moving between findings remounts with fresh state. */
export function FindingDetail() {
  const { id } = useParams<{ id: string }>();
  return id ? <FindingView key={id} id={id} /> : null;
}

function FindingView({ id }: { id: string }) {
  const navigate = useNavigate();
  const [finding, setFinding] = useState<FindingOut | null>(null);
  const [note, setNote] = useState("");
  const [selected, setSelected] = useState<TriageDecisionValue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [triageMessage, setTriageMessage] = useState<string | null>(null);
  const [allReviewed, setAllReviewed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<FindingOut>(`/findings/${id}`)
      .then((loaded) => {
        if (cancelled) return;
        setFinding(loaded);
        setSelected(loaded.triage_decision?.decision ?? null);
        setNote(loaded.triage_decision?.note ?? "");
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load finding.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const submitTriage = async (decision: TriageDecisionValue) => {
    setError(null);
    setAllReviewed(false);
    try {
      await api.post(`/findings/${id}/triage`, { decision, note: note || null });
      setSelected(decision);
      setTriageMessage(`Recorded: ${TRIAGE_LABELS[decision]}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record triage decision.");
    }
  };

  const goToNextPending = async () => {
    setError(null);
    try {
      const pending = await api.get<{ id: string }[]>("/findings?triage=pending");
      const next = pending.find((f) => f.id !== id);
      if (next) {
        navigate(`/findings/${next.id}`);
      } else {
        setAllReviewed(true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to look up the next finding.");
    }
  };

  if (error && !finding) {
    return (
      <GlassPanel className="mx-auto max-w-2xl">
        <p style={{ color: "var(--severity-critical)" }}>{error}</p>
      </GlassPanel>
    );
  }

  if (!finding) {
    return (
      <GlassPanel className="mx-auto max-w-2xl">
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel className="mx-auto max-w-2xl">
      <Link to="/review" className="text-sm underline" style={{ color: "var(--text-muted)" }}>
        &larr; Back to queue
      </Link>

      <div className="mt-3 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            {finding.clause.regulation.toUpperCase()} {finding.clause.clause_number}
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {finding.document.title} &middot; {finding.status}
          </p>
        </div>
        <SeverityChip severity={finding.severity} />
      </div>

      <p className="mt-4 text-sm">{finding.explanation}</p>

      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Clause text
      </h2>
      <p className="mt-1 text-sm">{finding.clause.requirement_text}</p>

      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Source passage &mdash; {finding.section.heading}
      </h2>
      <p className="mt-1 whitespace-pre-wrap text-sm">{finding.section.text}</p>

      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Triage
      </h2>
      <textarea
        className="mt-2 w-full rounded-lg border px-3 py-2 text-sm"
        style={{ borderColor: "var(--glass-border)" }}
        placeholder="Note (optional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
      />
      <div className="mt-2 flex gap-2">
        {DECISIONS.map(([value, label]) => {
          const active = selected === value;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={active}
              className={`rounded-lg border px-3 py-1.5 text-sm ${active ? "font-semibold" : ""}`}
              style={{
                borderColor: "var(--glass-border)",
                background: active ? "var(--surface-bg)" : "transparent",
                color: active ? "var(--surface-text)" : "inherit",
              }}
              onClick={() => submitTriage(value)}
            >
              {label}
            </button>
          );
        })}
      </div>

      {triageMessage && <p className="mt-2 text-sm" style={{ color: "var(--severity-resolved)" }}>{triageMessage}</p>}
      {error && <p className="mt-2 text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {selected && (
        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            className="rounded-lg border px-4 py-2 text-sm font-medium"
            style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
            onClick={goToNextPending}
          >
            Next pending finding &rarr;
          </button>
          {allReviewed && (
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              All findings reviewed. <Link to="/review" className="underline">Back to queue</Link>
            </span>
          )}
        </div>
      )}
    </GlassPanel>
  );
}
