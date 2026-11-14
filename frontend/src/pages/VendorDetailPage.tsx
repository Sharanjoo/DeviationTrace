import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { EmptyState, ProgressBar, type StatusDef } from "../components/CheckResults";
import { VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";
import { standardsMet, vendorAuditDate, vendorCounts, type VendorAuditDetail, type VendorDetail } from "../vendors";

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "partial", label: "Partial", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const INPUT = "mt-1.5 w-full rounded-lg border px-3 py-2 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)", color: "var(--text)" };
const muted = { color: "var(--text-muted)" };

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** One vendor: its previous audits, and a form to start a new one. */
export function VendorDetailPage() {
  const { vendorId } = useParams<{ vendorId: string }>();
  const navigate = useNavigate();
  const [vendor, setVendor] = useState<VendorDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api
      .get<VendorDetail>(`/vendors/${vendorId}`)
      .then(setVendor)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load vendor."));
  }, [vendorId]);

  if (error && !vendor) return <p className="text-center" style={{ color: "var(--severity-critical)" }}>{error}</p>;
  if (!vendor) return <p className="text-center" style={muted}>Loading vendor...</p>;

  const latest = vendor.latest_audit;
  const latestScore = latest ? standardsMet(latest) : null;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <Link to="/vendor-audit" className="text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
        ← All vendors
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="rounded-full px-2.5 py-0.5 text-xs font-medium" style={{ background: "var(--tint-violet)", color: "#6d28d9" }}>
            {VENDOR_CATEGORY_LABELS[vendor.vendor_category] ?? vendor.vendor_category}
          </span>
          <h1 className="mt-2 text-3xl font-bold">{vendor.name}</h1>
          <p className="mt-1 text-sm" style={muted}>
            {vendor.audit_count} audit{vendor.audit_count === 1 ? "" : "s"}
            {vendor.contact_name && ` · Contact: ${vendor.contact_name}`}
            {vendor.contact_email && ` (${vendor.contact_email})`}
          </p>
        </div>
        {!creating && (
          <button type="button" onClick={() => setCreating(true)} className="btn-primary px-5 py-2.5 text-sm">
            New audit
          </button>
        )}
      </div>

      {creating && (
        <NewVendorAuditForm
          vendor={vendor}
          onCancel={() => setCreating(false)}
          onCreated={(audit) => navigate(`/vendor-audit/audits/${audit.id}`)}
        />
      )}

      {latest && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="card p-5">
            <p className="text-xs" style={muted}>
              Latest audit
            </p>
            <p className="mt-1 text-lg font-semibold">{latest.audit_code}</p>
            <p className="text-xs" style={muted}>
              {vendorAuditDate(latest)}
            </p>
          </div>
          <div className="card p-5 sm:col-span-2">
            <div className="flex items-end justify-between">
              <p className="text-xs" style={muted}>
                Standards met in latest audit
              </p>
              <p className="text-3xl font-bold text-gradient">{latestScore === null ? "—" : `${latestScore}%`}</p>
            </div>
            <ProgressBar statuses={STATUSES} counts={vendorCounts(latest)} className="mt-3" />
            <p className="mt-2 text-xs" style={muted}>
              {latest.missing} missing · {latest.partial} partial · {latest.satisfied} satisfied
            </p>
          </div>
        </div>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Audit history</h2>
        {vendor.audits.length === 0 && !creating && (
          <EmptyState
            title="No audits for this vendor yet"
            body="Start a new audit by uploading the vendor's audit report. It's checked against the standards for this vendor's category straight away."
            actionLabel="New audit"
            onAction={() => setCreating(true)}
          />
        )}
        {vendor.audits.length > 0 && (
          <div className="card overflow-hidden">
            <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
              {vendor.audits.map((a) => {
                const score = standardsMet(a);
                return (
                  <li
                    key={a.id}
                    className="grid grid-cols-2 items-center gap-x-4 gap-y-2 px-5 py-4 md:grid-cols-[110px_1fr_80px_1.2fr_auto]"
                    style={{ borderColor: "var(--glass-border)" }}
                  >
                    <Link to={`/vendor-audit/audits/${a.id}`} className="whitespace-nowrap font-semibold hover:underline" style={{ color: "var(--brand-blue-text)" }}>
                      {a.audit_code}
                    </Link>
                    <div className="min-w-0 text-right md:text-left">
                      <p className="text-sm font-medium">{vendorAuditDate(a)}</p>
                      <p className="truncate text-xs" style={muted}>
                        {a.auditor_name ? `${a.auditor_name}${a.auditor_employee_id ? ` (${a.auditor_employee_id})` : ""}` : "Auditor not recorded"}
                      </p>
                    </div>
                    <span className="font-semibold">{score === null ? "—" : `${score}%`}</span>
                    <div className="col-span-2 md:col-span-1">
                      {a.document_status === "processed" ? (
                        <>
                          <ProgressBar statuses={STATUSES} counts={vendorCounts(a)} />
                          <p className="mt-1 text-xs" style={muted}>
                            {a.missing} missing · {a.partial} partial · {a.satisfied} satisfied
                          </p>
                        </>
                      ) : (
                        <p className="text-xs" style={{ color: "var(--severity-critical)" }}>
                          Report couldn't be read{a.processing_error ? `: ${a.processing_error}` : ""}
                        </p>
                      )}
                    </div>
                    <Link to={`/vendor-audit/audits/${a.id}`} className="btn-secondary col-span-2 w-fit px-3 py-1.5 text-xs md:col-span-1">
                      View
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}

function NewVendorAuditForm({
  vendor,
  onCancel,
  onCreated,
}: {
  vendor: VendorDetail;
  onCancel: () => void;
  onCreated: (audit: VendorAuditDetail) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [auditDate, setAuditDate] = useState(today());
  const [auditorName, setAuditorName] = useState("");
  const [auditorId, setAuditorId] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Choose the vendor's audit report to upload.");
      return;
    }
    setSubmitting(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    form.append("auditor_name", auditorName);
    form.append("auditor_employee_id", auditorId);
    if (auditDate) form.append("audit_date", auditDate);
    if (notes.trim()) form.append("notes", notes);
    try {
      onCreated(await api.upload<VendorAuditDetail>(`/vendors/${vendor.id}/audits`, form));
    } catch (err) {
      let message = err instanceof ApiError ? err.message : "Failed to create the audit.";
      try {
        const body = JSON.parse(message);
        message = typeof body.detail === "string" ? body.detail : body.detail?.[0]?.msg ?? message;
      } catch {
        // not JSON
      }
      setError(message);
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card p-6">
      <h2 className="text-lg font-semibold">New audit for {vendor.name}</h2>
      <p className="mt-0.5 text-sm" style={muted}>
        Upload the vendor's audit report. It's read and checked against the{" "}
        {VENDOR_CATEGORY_LABELS[vendor.vendor_category]?.toLowerCase() ?? vendor.vendor_category} standards as soon as you
        submit.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-medium">
          Audit date
          <input type="date" className={INPUT} style={INPUT_STYLE} value={auditDate} onChange={(e) => setAuditDate(e.target.value)} />
        </label>
        <label className="text-sm font-medium">
          Auditor name <span style={{ color: "var(--severity-critical)" }}>*</span>
          <input className={INPUT} style={INPUT_STYLE} value={auditorName} onChange={(e) => setAuditorName(e.target.value)} required autoComplete="off" />
        </label>
        <label className="text-sm font-medium">
          Auditor employee ID <span style={{ color: "var(--severity-critical)" }}>*</span>
          <input
            className={INPUT}
            style={INPUT_STYLE}
            value={auditorId}
            onChange={(e) => setAuditorId(e.target.value)}
            placeholder="e.g. EMP-1042"
            required
            autoComplete="off"
          />
        </label>
        <div className="sm:col-span-3">
          <p className="text-sm font-medium">
            Audit report <span style={{ color: "var(--severity-critical)" }}>*</span>
          </p>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              setFile(e.dataTransfer.files[0] ?? null);
            }}
            className="mt-1.5 flex w-full flex-col items-center rounded-xl border-2 border-dashed px-4 py-6 text-sm"
            style={{ borderColor: file ? "var(--brand-blue)" : "var(--glass-border)", background: file ? "var(--tint-blue)" : "#fff" }}
          >
            {file ? (
              <span className="font-medium [overflow-wrap:anywhere]">{file.name}</span>
            ) : (
              <span style={muted}>Click to choose, or drop the report here (.pdf, .docx, .txt)</span>
            )}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <label className="text-sm font-medium sm:col-span-3">
          Notes
          <textarea className={INPUT} style={INPUT_STYLE} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
      </div>
      {error && <p className="mt-3 text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>}
      <div className="mt-5 flex gap-2">
        <button type="submit" disabled={submitting} className="btn-primary px-4 py-2 text-sm">
          {submitting ? "Uploading and checking..." : "Upload and run cross-check"}
        </button>
        <button type="button" onClick={onCancel} disabled={submitting} className="btn-secondary px-4 py-2 text-sm">
          Cancel
        </button>
      </div>
    </form>
  );
}
