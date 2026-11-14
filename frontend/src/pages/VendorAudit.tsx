import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { CheckHeader, EmptyState, ProgressBar, type StatusDef } from "../components/CheckResults";
import { DEPARTMENT_LABELS, VENDOR_CATEGORIES_BY_DEPARTMENT, VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";
import {
  displayFileName,
  standardsMet,
  vendorAuditDate,
  vendorCounts,
  type UnassignedReport,
  type Vendor,
  type VendorAuditDetail,
  type VendorDetail,
} from "../vendors";

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "partial", label: "Partial", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const INPUT = "mt-1.5 w-full rounded-lg border px-3 py-2 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)", color: "var(--text)" };
const muted = { color: "var(--text-muted)" };
const EMPTY_VENDOR = { name: "", vendor_category: "raw_material_supplier", contact_name: "", contact_email: "", notes: "" };

/** Vendor audit home: the org's vendors, each with its latest audit. Open a
 * vendor to see its audit history or start a new audit. */
export function VendorAudit() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const departmentFilter = params.get("department");
  const categoryFilter = params.get("category") ?? "";
  const q = params.get("q") ?? "";

  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [unassigned, setUnassigned] = useState<UnassignedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(EMPTY_VENDOR);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([api.get<Vendor[]>("/vendors"), api.get<UnassignedReport[]>("/vendors/unassigned-reports")])
      .then(([v, u]) => {
        setVendors(v);
        setUnassigned(u);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load vendors."))
      .finally(() => setLoading(false));
  }, []);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  // A ?department= link (from a department checklist page) narrows to the
  // vendor categories that department audits.
  const allowedCategories = departmentFilter ? VENDOR_CATEGORIES_BY_DEPARTMENT[departmentFilter] ?? [] : null;
  const needle = q.trim().toLowerCase();
  const visible = vendors.filter(
    (v) =>
      (!allowedCategories || allowedCategories.includes(v.vendor_category)) &&
      (!categoryFilter || v.vendor_category === categoryFilter) &&
      (!needle || [v.name, v.contact_name].join(" ").toLowerCase().includes(needle)),
  );
  const categoryOptions = (allowedCategories ?? Object.keys(VENDOR_CATEGORY_LABELS)).filter((c) =>
    vendors.some((v) => v.vendor_category === c),
  );

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const vendor = await api.post<VendorDetail>("/vendors", form);
      navigate(`/vendor-audit/vendors/${vendor.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? readable(err.message) : "Failed to add vendor.");
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <CheckHeader
        eyebrow="Verification check"
        title="Vendor audit cross-check"
        description="Your vendors, each with its audit history. Open a vendor to review previous audits or start a new one; each audit's report is checked against the standards for that vendor's category."
        action={
          !adding && (
            <button type="button" onClick={() => setAdding(true)} className="btn-primary px-5 py-2.5 text-sm">
              Add vendor
            </button>
          )
        }
      />

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {adding && (
        <form onSubmit={handleCreate} className="card p-6">
          <h2 className="text-lg font-semibold">Add a vendor</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">
              Vendor name <span style={{ color: "var(--severity-critical)" }}>*</span>
              <input
                className={INPUT}
                style={INPUT_STYLE}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Acme Excipient Supplier"
                required
                maxLength={255}
              />
            </label>
            <label className="text-sm font-medium">
              Vendor category <span style={{ color: "var(--severity-critical)" }}>*</span>
              <select
                className={INPUT}
                style={INPUT_STYLE}
                value={form.vendor_category}
                onChange={(e) => setForm({ ...form, vendor_category: e.target.value })}
              >
                {Object.entries(VENDOR_CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium">
              Vendor contact
              <input
                className={INPUT}
                style={INPUT_STYLE}
                value={form.contact_name}
                onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
                placeholder="Name at the vendor"
              />
            </label>
            <label className="text-sm font-medium">
              Contact email
              <input
                type="email"
                className={INPUT}
                style={INPUT_STYLE}
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
              />
            </label>
          </div>
          <div className="mt-5 flex gap-2">
            <button type="submit" disabled={saving} className="btn-primary px-4 py-2 text-sm">
              {saving ? "Adding..." : "Add vendor"}
            </button>
            <button
              type="button"
              onClick={() => {
                setAdding(false);
                setForm(EMPTY_VENDOR);
              }}
              className="btn-secondary px-4 py-2 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {departmentFilter && (
        <div className="card flex items-center justify-between gap-4 px-5 py-3 text-sm">
          <p>
            Showing vendors audited by <strong>{DEPARTMENT_LABELS[departmentFilter] ?? departmentFilter}</strong>
          </p>
          <button type="button" onClick={() => setParam("department", "")} className="btn-secondary px-3 py-1.5 text-xs">
            Show all
          </button>
        </div>
      )}

      {loading && <p style={muted}>Loading vendors...</p>}

      {!loading && vendors.length === 0 && !adding && (
        <EmptyState
          title="No vendors yet"
          body="Add a vendor, then start an audit for it by uploading the vendor's audit report. Each audit is kept in the vendor's history with an ID like VA-0001."
          actionLabel="Add vendor"
          onAction={() => setAdding(true)}
        />
      )}

      {vendors.length > 0 && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <input
              className="w-full max-w-xs rounded-lg border px-3 py-2 text-sm"
              style={INPUT_STYLE}
              value={q}
              onChange={(e) => setParam("q", e.target.value)}
              placeholder="Search vendors..."
            />
            <div className="flex flex-wrap gap-2">
              {["", ...categoryOptions].map((c) => {
                const on = categoryFilter === c;
                return (
                  <button
                    key={c || "all"}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setParam("category", c)}
                    className="rounded-full border px-3.5 py-1.5 text-sm font-medium"
                    style={
                      on
                        ? { background: "var(--tint-blue)", borderColor: "var(--brand-blue)", color: "var(--brand-blue-text)" }
                        : { background: "#fff", borderColor: "var(--glass-border)", color: "#4b5563" }
                    }
                  >
                    {c ? VENDOR_CATEGORY_LABELS[c] : "All categories"}
                  </button>
                );
              })}
            </div>
          </div>

          {visible.length === 0 && (
            <div className="card p-6 text-sm" style={muted}>
              No vendors match.
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {visible.map((v) => {
              const latest = v.latest_audit;
              const score = latest ? standardsMet(latest) : null;
              return (
                <Link key={v.id} to={`/vendor-audit/vendors/${v.id}`} className="card flex flex-col p-5 transition-shadow hover:shadow-md">
                  <span className="w-fit rounded-full px-2.5 py-0.5 text-xs font-medium" style={{ background: "var(--tint-violet)", color: "#6d28d9" }}>
                    {VENDOR_CATEGORY_LABELS[v.vendor_category] ?? v.vendor_category}
                  </span>
                  <h2 className="mt-2 text-lg font-semibold [overflow-wrap:anywhere]">{v.name}</h2>
                  <p className="text-xs" style={muted}>
                    {v.audit_count} audit{v.audit_count === 1 ? "" : "s"}
                    {v.contact_name && ` · Contact: ${v.contact_name}`}
                  </p>
                  <div className="mt-4 flex-1 border-t pt-4" style={{ borderColor: "var(--glass-border)" }}>
                    {latest ? (
                      <>
                        <div className="flex items-end justify-between gap-3">
                          <div>
                            <p className="text-xs" style={muted}>
                              Latest audit
                            </p>
                            <p className="text-sm font-semibold">
                              {latest.audit_code} · {vendorAuditDate(latest)}
                            </p>
                          </div>
                          <p className="text-2xl font-bold text-gradient">{score === null ? "—" : `${score}%`}</p>
                        </div>
                        <ProgressBar statuses={STATUSES} counts={vendorCounts(latest)} className="mt-3" />
                      </>
                    ) : (
                      <p className="text-sm" style={muted}>
                        No audits yet.
                      </p>
                    )}
                  </div>
                  <span className="mt-4 text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
                    Open vendor →
                  </span>
                </Link>
              );
            })}
          </div>
        </>
      )}

      {unassigned.length > 0 && (
        <UnassignedReports reports={unassigned} vendors={vendors} onAssigned={(auditId) => navigate(`/vendor-audit/audits/${auditId}`)} />
      )}
    </div>
  );
}

function UnassignedReports({
  reports,
  vendors,
  onAssigned,
}: {
  reports: UnassignedReport[];
  vendors: Vendor[];
  onAssigned: (auditId: string) => void;
}) {
  const [choice, setChoice] = useState<Record<string, string>>({});
  // When each audit actually happened; defaults to the report's upload day.
  const [dates, setDates] = useState<Record<string, string>>({});
  const dateFor = (r: UnassignedReport) => dates[r.id] ?? localDay(r.uploaded_at);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const assign = async (report: UnassignedReport) => {
    const vendorId = choice[report.id];
    if (!vendorId) return;
    setBusyId(report.id);
    setError(null);
    try {
      const audit = await api.post<VendorAuditDetail>(`/vendors/${vendorId}/assign-report`, {
        document_id: report.id,
        audit_date: dateFor(report) || null,
      });
      onAssigned(audit.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to attach report.");
      setBusyId(null);
    }
  };

  return (
    <section className="card overflow-hidden">
      <header className="border-b px-5 py-4" style={{ borderColor: "var(--glass-border)" }}>
        <h2 className="text-lg font-semibold">Unassigned reports ({reports.length})</h2>
        <p className="text-sm" style={muted}>
          Vendor audit reports uploaded before vendors existed. Attach each one to its vendor to add it to that vendor's
          audit history.
        </p>
        {error && <p className="mt-2 text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>}
      </header>
      <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
        {reports.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center gap-3 px-5 py-3" style={{ borderColor: "var(--glass-border)" }}>
            <div className="min-w-0 flex-1">
              <p className="font-medium [overflow-wrap:anywhere]">{displayFileName(r.title)}</p>
              <p className="text-xs" style={muted}>
                {r.vendor_category ? VENDOR_CATEGORY_LABELS[r.vendor_category] : "No category"} · uploaded{" "}
                {new Date(r.uploaded_at).toLocaleDateString()}
              </p>
            </div>
            {vendors.length === 0 ? (
              <span className="text-xs" style={muted}>
                Add a vendor first
              </span>
            ) : (
              <>
                <select
                  className="rounded-lg border px-3 py-2 text-sm"
                  style={INPUT_STYLE}
                  value={choice[r.id] ?? ""}
                  onChange={(e) => setChoice({ ...choice, [r.id]: e.target.value })}
                >
                  <option value="">Choose vendor...</option>
                  {vendors.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-xs" style={muted}>
                  Audit date
                  <input
                    type="date"
                    className="rounded-lg border px-2 py-1.5 text-sm"
                    style={INPUT_STYLE}
                    value={dateFor(r)}
                    onChange={(e) => setDates({ ...dates, [r.id]: e.target.value })}
                  />
                </label>
                <button
                  type="button"
                  disabled={!choice[r.id] || busyId === r.id}
                  onClick={() => assign(r)}
                  className="btn-primary px-3 py-2 text-xs"
                >
                  {busyId === r.id ? "Attaching..." : "Attach"}
                </button>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** "YYYY-MM-DD" in the viewer's time zone. */
function localDay(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** FastAPI error bodies are JSON; show their message plainly. */
function readable(message: string): string {
  try {
    const body = JSON.parse(message);
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // not JSON
  }
  return message;
}
