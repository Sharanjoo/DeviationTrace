import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { GroupCard, ResultRow, StatCards, type StatusDef } from "../components/CheckResults";
import { countBy } from "../countBy";
import { VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";
import { displayFileName, vendorAuditDate, type VendorAuditDetail } from "../vendors";

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "partial", label: "Partial", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const STATUS_BY_VALUE = Object.fromEntries(STATUSES.map((s) => [s.value, s]));
const muted = { color: "var(--text-muted)" };

/** One vendor audit (VA-0001): who audited when, the report, and how it
 * measured up against the vendor category's standards. */
export function VendorAuditDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [audit, setAudit] = useState<VendorAuditDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [rerunning, setRerunning] = useState(false);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    api
      .get<VendorAuditDetail>(`/vendor-audits/${auditId}`)
      .then(setAudit)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load this audit."));
  }, [auditId]);

  const handleRerun = async () => {
    setRerunning(true);
    setError(null);
    try {
      setAudit(await api.post<VendorAuditDetail>(`/vendor-audits/${auditId}/rerun`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
    } finally {
      setRerunning(false);
    }
  };

  if (!audit) {
    return error ? (
      <p className="text-center" style={{ color: "var(--severity-critical)" }}>
        {error}
      </p>
    ) : (
      <p className="text-center" style={muted}>
        Loading audit...
      </p>
    );
  }

  const shown = audit.findings.filter((f) => !statusFilter || f.status === statusFilter);
  const details = [
    { label: "Audit date", value: vendorAuditDate(audit) },
    {
      label: "Auditor",
      value: audit.auditor_name
        ? `${audit.auditor_name}${audit.auditor_employee_id ? ` (${audit.auditor_employee_id})` : ""}`
        : "Not recorded",
    },
    { label: "Report", value: displayFileName(audit.document_title) },
  ];

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <Link
        to={`/vendor-audit/vendors/${audit.vendor_id}`}
        className="text-sm font-medium"
        style={{ color: "var(--brand-blue-text)" }}
      >
        ← {audit.vendor_name}
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Vendor audit</p>
          <h1 className="mt-2 text-3xl font-bold">
            {audit.audit_code} · {audit.vendor_name}
          </h1>
          <p className="mt-1 text-sm" style={muted}>
            Checked against the {VENDOR_CATEGORY_LABELS[audit.vendor_category]?.toLowerCase() ?? audit.vendor_category}{" "}
            standards.
          </p>
        </div>
        {audit.document_status === "processed" && (
          <button type="button" onClick={handleRerun} disabled={rerunning} className="btn-secondary px-4 py-2 text-sm">
            {rerunning ? "Checking..." : "Run cross-check again"}
          </button>
        )}
      </div>

      {editing ? (
        <EditAuditDetails
          audit={audit}
          onCancel={() => setEditing(false)}
          onSaved={(updated) => {
            setAudit(updated);
            setEditing(false);
          }}
        />
      ) : (
        <section className="card p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="font-semibold">Audit details</h2>
            <button type="button" onClick={() => setEditing(true)} className="btn-secondary px-3 py-1.5 text-xs">
              Edit details
            </button>
          </div>
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-3">
            {details.map((d) => (
              <div key={d.label}>
                <dt className="text-xs" style={muted}>
                  {d.label}
                </dt>
                <dd className="mt-0.5 font-semibold [overflow-wrap:anywhere]">{d.value}</dd>
              </div>
            ))}
          </dl>
          {audit.notes && (
            <p className="mt-4 text-sm" style={muted}>
              <span className="font-medium" style={{ color: "var(--text)" }}>
                Notes:
              </span>{" "}
              {audit.notes}
            </p>
          )}
        </section>
      )}

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {audit.document_status !== "processed" ? (
        <div className="card p-6 text-sm" style={{ color: "var(--severity-critical)" }}>
          The audit report couldn't be read{audit.processing_error ? `: ${audit.processing_error}` : "."} Start a new
          audit for this vendor with a readable copy of the report.
        </div>
      ) : (
        <>
          <StatCards
            scoreLabel="Standards met"
            statuses={STATUSES}
            counts={countBy(audit.findings, (f) => f.status)}
            active={statusFilter}
            onSelect={setStatusFilter}
          />
          <GroupCard
            title="Standards checked"
            subtitle={`${audit.findings.length} standard${audit.findings.length === 1 ? "" : "s"} for this vendor category`}
            statuses={STATUSES}
            counts={countBy(audit.findings, (f) => f.status)}
          >
            {shown.map((f) => (
              <ResultRow
                key={f.id}
                status={STATUS_BY_VALUE[f.status]}
                title={f.requirement_name}
                citation={f.citation}
                explanation={f.explanation}
              />
            ))}
          </GroupCard>
        </>
      )}
    </div>
  );
}

const INPUT = "mt-1.5 w-full rounded-lg border px-3 py-2 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)", color: "var(--text)" };

/** Correct an audit's date, auditor or notes. The report and its results
 * stay as they are. */
function EditAuditDetails({
  audit,
  onCancel,
  onSaved,
}: {
  audit: VendorAuditDetail;
  onCancel: () => void;
  onSaved: (audit: VendorAuditDetail) => void;
}) {
  const [auditDate, setAuditDate] = useState(audit.audit_date ?? "");
  const [auditorName, setAuditorName] = useState(audit.auditor_name ?? "");
  const [auditorId, setAuditorId] = useState(audit.auditor_employee_id ?? "");
  const [notes, setNotes] = useState(audit.notes ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onSaved(
        await api.patch<VendorAuditDetail>(`/vendor-audits/${audit.id}`, {
          audit_date: auditDate || null,
          auditor_name: auditorName,
          auditor_employee_id: auditorId,
          notes,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed.");
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card p-6">
      <h2 className="font-semibold">Edit audit details</h2>
      <p className="mt-0.5 text-sm" style={muted}>
        The report and its results don't change. To check a different report, start a new audit for this vendor.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <label className="text-sm font-medium">
          Audit date
          <input
            type="date"
            className={INPUT}
            style={INPUT_STYLE}
            value={auditDate}
            onChange={(e) => setAuditDate(e.target.value)}
          />
        </label>
        <label className="text-sm font-medium">
          Auditor name
          <input
            className={INPUT}
            style={INPUT_STYLE}
            value={auditorName}
            onChange={(e) => setAuditorName(e.target.value)}
            autoComplete="off"
          />
        </label>
        <label className="text-sm font-medium">
          Auditor employee ID
          <input
            className={INPUT}
            style={INPUT_STYLE}
            value={auditorId}
            onChange={(e) => setAuditorId(e.target.value)}
            autoComplete="off"
          />
        </label>
        <label className="text-sm font-medium sm:col-span-3">
          Notes
          <textarea
            className={INPUT}
            style={INPUT_STYLE}
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
      </div>
      {error && (
        <p className="mt-3 text-sm" style={{ color: "var(--severity-critical)" }}>
          {error}
        </p>
      )}
      <div className="mt-5 flex gap-2">
        <button type="submit" disabled={saving} className="btn-primary px-4 py-2 text-sm">
          {saving ? "Saving..." : "Save details"}
        </button>
        <button type="button" onClick={onCancel} disabled={saving} className="btn-secondary px-4 py-2 text-sm">
          Cancel
        </button>
      </div>
    </form>
  );
}
