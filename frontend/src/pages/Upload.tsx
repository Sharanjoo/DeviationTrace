import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";

interface DocumentOut {
  id: string;
}

// Only the two process areas the seeded clause library actually covers.
// Offering the PRD's other example areas (complaint handling, design
// controls) here would silently produce zero findings.
const PROCESS_AREAS = [
  { value: "deviation_handling", label: "Deviation handling" },
  { value: "capa", label: "CAPA" },
];

const DOCUMENT_TYPES = [
  { value: "sop", label: "SOP" },
  { value: "deviation", label: "Deviation report" },
  { value: "batch_record", label: "Batch / device record" },
];
// This is the SOP & deviation check's "Add document". The other checks take
// documents where they're used: department reports in a new internal audit
// simulation (step 2), vendor audit reports on the vendor's page.

export function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState("sop");
  const [processArea, setProcessArea] = useState("deviation_handling");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("type", type);
      formData.append("file", file);
      formData.append("process_area", processArea);
      const document = await api.upload<DocumentOut>("/documents", formData);
      navigate(`/processing/${document.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <GlassPanel className="mx-auto max-w-2xl">
      <p className="eyebrow">SOP &amp; deviations</p>
      <h1 className="mt-2 text-3xl font-bold">Add a document</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Add an SOP, deviation report, or batch/device record (PDF, Word, or text). It's split into sections and
        cross-checked against the QMSR, ISO 13485 and 21 CFR 211 clause library on the next screen.
      </p>
      <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
        Department reports are added in a new internal audit simulation, and vendor audit reports on the vendor's page.
      </p>

      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
        <div
          className="flex h-32 items-center justify-center rounded-2xl border-2 border-dashed"
          style={{ borderColor: "var(--glass-border)" }}
        >
          <label className="cursor-pointer text-sm" style={{ color: "var(--text-muted)" }}>
            {file ? file.name : "Choose a file (.pdf, .docx, .txt)"}
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        <div className="flex gap-4">
          <label className="flex-1 text-sm">
            Document type
            <select
              className="mt-1 w-full rounded-lg border px-3 py-2"
              style={{ borderColor: "var(--glass-border)" }}
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex-1 text-sm">
            Process area
            <select
              className="mt-1 w-full rounded-lg border px-3 py-2"
              style={{ borderColor: "var(--glass-border)" }}
              value={processArea}
              onChange={(e) => setProcessArea(e.target.value)}
            >
              {PROCESS_AREAS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

        <button type="submit" disabled={submitting} className="btn-primary px-4 py-2">
          {submitting ? "Uploading..." : "Upload and process"}
        </button>
      </form>
    </GlassPanel>
  );
}
