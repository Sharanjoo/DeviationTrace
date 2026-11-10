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
  { value: "report", label: "Department report" },
  { value: "vendor_audit_report", label: "Vendor audit report" },
];

// The internal-audit checklist departments (Phase 1). Department reports
// don't have a meaningful process area, so the backend just wants the
// fixed placeholder "general" — see the report-branch in handleSubmit.
const DEPARTMENTS = [
  { value: "qc", label: "QC" },
  { value: "qa", label: "QA" },
  { value: "utilities", label: "Utilities" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "engineering", label: "Engineering" },
];

// The vendor/material categories the vendor-standards library covers
// (Phase 2). Same "general" process-area placeholder as department reports.
const VENDOR_CATEGORIES = [
  { value: "raw_material_supplier", label: "Raw material supplier" },
  { value: "contract_manufacturer", label: "Contract manufacturer" },
  { value: "calibration_test_service", label: "Calibration / test service" },
  { value: "sterilization_service", label: "Sterilization service" },
  { value: "packaging_component_supplier", label: "Packaging component supplier" },
];

export function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState("sop");
  const [processArea, setProcessArea] = useState("deviation_handling");
  const [department, setDepartment] = useState("qc");
  const [vendorCategory, setVendorCategory] = useState("raw_material_supplier");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isDepartmentReport = type === "report";
  const isVendorAuditReport = type === "vendor_audit_report";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    if (isDepartmentReport && !department) {
      setError("Choose a department.");
      return;
    }
    if (isVendorAuditReport && !vendorCategory) {
      setError("Choose a vendor category.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("type", type);
      formData.append("file", file);
      if (isDepartmentReport) {
        formData.append("process_area", "general");
        formData.append("department", department);
      } else if (isVendorAuditReport) {
        formData.append("process_area", "general");
        formData.append("vendor_category", vendorCategory);
      } else {
        formData.append("process_area", processArea);
      }
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
      <h1 className="text-3xl font-bold">Upload a document</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Upload a SOP, deviation report, or batch/device record (PDF, Word, or
        text). Document type and process area are recorded now; the pipeline
        classifies and cross-checks it against the clause library on the next
        screen.
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

          {isDepartmentReport ? (
            <label className="flex-1 text-sm">
              Department
              <select
                className="mt-1 w-full rounded-lg border px-3 py-2"
                style={{ borderColor: "var(--glass-border)" }}
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              >
                {DEPARTMENTS.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
            </label>
          ) : isVendorAuditReport ? (
            <label className="flex-1 text-sm">
              Vendor category
              <select
                className="mt-1 w-full rounded-lg border px-3 py-2"
                style={{ borderColor: "var(--glass-border)" }}
                value={vendorCategory}
                onChange={(e) => setVendorCategory(e.target.value)}
              >
                {VENDOR_CATEGORIES.map((v) => (
                  <option key={v.value} value={v.value}>
                    {v.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
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
          )}
        </div>

        {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="btn-primary px-4 py-2"
        >
          {submitting ? "Uploading..." : "Upload and process"}
        </button>
      </form>
    </GlassPanel>
  );
}
