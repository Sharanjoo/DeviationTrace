import { useEffect, useMemo, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface FindingOut {
  severity: string;
  document: { type: string };
}

export function ReportExport() {
  const { orgId } = useAuth();
  const [findings, setFindings] = useState<FindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api
      .get<FindingOut[]>("/findings")
      .then(setFindings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load findings."));
  }, []);

  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const finding of findings) {
      counts[finding.severity] = (counts[finding.severity] ?? 0) + 1;
    }
    return counts;
  }, [findings]);

  const processAreaCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const finding of findings) {
      counts[finding.document.type] = (counts[finding.document.type] ?? 0) + 1;
    }
    return counts;
  }, [findings]);

  const handleDownload = async () => {
    if (!orgId) return;
    setDownloading(true);
    setError(null);
    try {
      const blob = await api.downloadBlob(`/reports/${orgId}/export`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "deviationtrace-report.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download report.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <GlassPanel className="mx-auto max-w-2xl">
      <h1 className="text-3xl font-bold">Report export</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Summary across all processed documents for this organization.
      </p>

      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        By severity
      </h2>
      <ul className="mt-1 text-sm">
        {Object.entries(severityCounts).map(([severity, count]) => (
          <li key={severity}>
            {severity}: {count}
          </li>
        ))}
        {findings.length === 0 && <li>No findings yet.</li>}
      </ul>

      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        By document type
      </h2>
      <ul className="mt-1 text-sm">
        {Object.entries(processAreaCounts).map(([type, count]) => (
          <li key={type}>
            {type}: {count}
          </li>
        ))}
      </ul>

      {error && <p className="mt-4" style={{ color: "var(--severity-critical)" }}>{error}</p>}

      <button
        type="button"
        disabled={downloading}
        onClick={handleDownload}
        className="mt-6 btn-primary px-4 py-2"
      >
        {downloading ? "Preparing PDF..." : "Download PDF report"}
      </button>
    </GlassPanel>
  );
}
