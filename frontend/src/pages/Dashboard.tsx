import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { GlassPanel, SeverityChip, TriageChip } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import type { TriageDecisionValue } from "../triage";

interface FindingOut {
  id: string;
  document: { id: string; title: string; type: string };
  clause: { regulation: string; clause_number: string };
  status: string;
  severity: "critical" | "major" | "minor";
  explanation: string;
  triage_decision: { decision: TriageDecisionValue } | null;
}

const SEVERITIES = ["critical", "major", "minor"];
const STATUSES = ["missing", "partial", "contradicted"];

export function Dashboard() {
  const [searchParams] = useSearchParams();
  const documentId = searchParams.get("document_id");

  const [findings, setFindings] = useState<FindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    const path = documentId ? `/findings?document_id=${documentId}` : "/findings";
    setLoading(true);
    api
      .get<FindingOut[]>(path)
      .then(setFindings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load findings."))
      .finally(() => setLoading(false));
  }, [documentId]);

  const filtered = useMemo(
    () =>
      findings.filter(
        (f) => (!severityFilter || f.severity === severityFilter) && (!statusFilter || f.status === statusFilter),
      ),
    [findings, severityFilter, statusFilter],
  );

  const grouped = useMemo(() => {
    const groups = new Map<string, { title: string; findings: FindingOut[] }>();
    for (const finding of filtered) {
      const key = finding.document.id;
      if (!groups.has(key)) {
        groups.set(key, { title: finding.document.title, findings: [] });
      }
      groups.get(key)!.findings.push(finding);
    }
    return Array.from(groups.values());
  }, [filtered]);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-3xl font-bold">Findings</h1>

      <div className="flex gap-4 text-sm">
        <select
          className="rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--glass-border)" }}
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
        >
          <option value="">All severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--glass-border)" }}
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
      {!loading && !error && filtered.length === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>No findings match these filters.</p>
        </GlassPanel>
      )}

      {grouped.map((group) => (
        <div key={group.title} className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
            {group.title}
          </h2>
          {group.findings.map((finding) => (
            <Link key={finding.id} to={`/findings/${finding.id}`}>
              <GlassPanel className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium">
                    {finding.clause.regulation.toUpperCase()} {finding.clause.clause_number}
                  </div>
                  <p className="mt-2 text-sm">{finding.explanation}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <SeverityChip severity={finding.severity} />
                  <TriageChip decision={finding.triage_decision?.decision} />
                </div>
              </GlassPanel>
            </Link>
          ))}
        </div>
      ))}
    </div>
  );
}
