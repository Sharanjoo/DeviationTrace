import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { GlassPanel, SeverityChip } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";

interface FindingOut {
  id: string;
  document: { id: string; title: string; type: string };
  section: { heading: string; text: string };
  clause: { regulation: string; clause_number: string; requirement_text: string };
  status: string;
  severity: "critical" | "major" | "minor";
  explanation: string;
}

const DECISIONS: { value: string; label: string }[] = [
  { value: "confirmed", label: "Confirmed" },
  { value: "false_positive", label: "False positive" },
  { value: "needs_sme", label: "Needs SME" },
];

export function FindingDetail() {
  const { id } = useParams<{ id: string }>();
  const [finding, setFinding] = useState<FindingOut | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [triageMessage, setTriageMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get<FindingOut>(`/findings/${id}`)
      .then(setFinding)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load finding."));
  }, [id]);

  const submitTriage = async (decision: string) => {
    if (!id) return;
    setError(null);
    try {
      await api.post(`/findings/${id}/triage`, { decision, note: note || null });
      setTriageMessage(`Recorded: ${decision.replace("_", " ")}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record triage decision.");
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
      <div className="flex items-center justify-between">
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
        {DECISIONS.map((decision) => (
          <button
            key={decision.value}
            type="button"
            className="rounded-lg border px-3 py-1.5 text-sm"
            style={{ borderColor: "var(--glass-border)" }}
            onClick={() => submitTriage(decision.value)}
          >
            {decision.label}
          </button>
        ))}
      </div>

      {triageMessage && <p className="mt-2 text-sm" style={{ color: "var(--severity-resolved)" }}>{triageMessage}</p>}
      {error && <p className="mt-2 text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>}
    </GlassPanel>
  );
}
