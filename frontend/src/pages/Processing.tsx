import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";

interface DocumentStatusOut {
  id: string;
  status: string;
  detected_process_area: string | null;
  processing_error: string | null;
}

const STEPS = ["Classify", "Extract", "Cross-check"];
const POLL_INTERVAL_MS = 1500;

export function Processing() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [status, setStatus] = useState<DocumentStatusOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) return;

    // No "only run once" guard here: React 18 StrictMode's dev-only double
    // invoke would otherwise race a guard flag against the `cancelled` closure
    // below and silently drop the real result. Processing is idempotent
    // (Milestone 3), so letting StrictMode's replay redo the call is fine —
    // in production, effects only run once anyway.
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const current = await api.get<DocumentStatusOut>(`/documents/${documentId}/status`);
        if (cancelled) return;
        setStatus(current);
        if (current.status !== "processed" && current.status !== "failed") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to check status.");
      }
    };

    const start = async () => {
      try {
        const result = await api.post<DocumentStatusOut>(`/documents/${documentId}/process`);
        if (cancelled) return;
        setStatus(result);
        if (result.status !== "processed" && result.status !== "failed") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to start processing.");
      }
    };

    start();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [documentId]);

  const isDone = status?.status === "processed";
  const isFailed = status?.status === "failed";
  const stepReached = (index: number) => isDone || isFailed || index === 0;

  return (
    <GlassPanel className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold">Processing</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Status: {status?.status ?? "starting..."}
      </p>

      <ol className="mt-6 space-y-3">
        {STEPS.map((step, index) => (
          <li
            key={step}
            className="rounded-xl border px-4 py-3"
            style={{
              borderColor: "var(--glass-border)",
              opacity: stepReached(index) ? 1 : 0.5,
            }}
          >
            {step}
          </li>
        ))}
      </ol>

      {isFailed && (
        <p className="mt-4" style={{ color: "var(--severity-critical)" }}>
          Processing failed: {status?.processing_error}
        </p>
      )}
      {error && <p className="mt-4" style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {isDone && (
        <button
          type="button"
          className="mt-6 rounded-lg border px-4 py-2 font-medium"
          style={{ borderColor: "var(--glass-border)" }}
          onClick={() => navigate(`/findings?document_id=${documentId}`)}
        >
          View findings
        </button>
      )}
    </GlassPanel>
  );
}
