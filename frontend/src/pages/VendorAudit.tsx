import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { GlassPanel, SeverityChip } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { DEPARTMENT_LABELS, VENDOR_CATEGORIES_BY_DEPARTMENT, VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";

interface VendorDocumentOut {
  id: string;
  title: string;
  vendor_category: string | null;
  status: string;
  processing_error: string | null;
}

interface VendorAuditFindingOut {
  id: string;
  document: { id: string; title: string };
  standard: { vendor_category: string; requirement_name: string; citation: string };
  status: "missing" | "partial" | "satisfied";
  severity: "critical" | "major" | "resolved";
  explanation: string;
}

const STATUSES = ["missing", "partial", "satisfied"];

export function VendorAudit() {
  const [searchParams, setSearchParams] = useSearchParams();
  const departmentFilter = searchParams.get("department");
  const categoriesForDepartment = departmentFilter ? VENDOR_CATEGORIES_BY_DEPARTMENT[departmentFilter] ?? [] : null;

  const [documents, setDocuments] = useState<VendorDocumentOut[]>([]);
  const [findings, setFindings] = useState<VendorAuditFindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [vendorCategoryFilter, setVendorCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const loadAll = () => {
    setLoading(true);
    Promise.all([
      api.get<VendorDocumentOut[]>("/documents?type=vendor_audit_report"),
      api.get<VendorAuditFindingOut[]>("/vendor-audit/findings"),
    ])
      .then(([docs, foundFindings]) => {
        setDocuments(docs);
        setFindings(foundFindings);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load vendor audit data."))
      .finally(() => setLoading(false));
  };

  useEffect(loadAll, []);

  const handleRun = async (documentId: string) => {
    setRunningId(documentId);
    setError(null);
    try {
      await api.post(`/vendor-audit/${documentId}/run`);
      loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
    } finally {
      setRunningId(null);
    }
  };

  const findingsByDocument = useMemo(() => {
    const map = new Map<string, VendorAuditFindingOut[]>();
    for (const finding of findings) {
      if (statusFilter && finding.status !== statusFilter) continue;
      const key = finding.document.id;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(finding);
    }
    return map;
  }, [findings, statusFilter]);

  const visibleDocuments = useMemo(
    () =>
      documents.filter((d) => {
        if (categoriesForDepartment && !(d.vendor_category && categoriesForDepartment.includes(d.vendor_category))) {
          return false;
        }
        return !vendorCategoryFilter || d.vendor_category === vendorCategoryFilter;
      }),
    [documents, vendorCategoryFilter, categoriesForDepartment],
  );

  const categoryLabel = (value: string | null) => (value ? VENDOR_CATEGORY_LABELS[value] ?? value : "—");

  const summarize = (rows: VendorAuditFindingOut[]) => {
    const counts = { missing: 0, partial: 0, satisfied: 0 };
    for (const row of rows) counts[row.status] += 1;
    return STATUSES.filter((s) => counts[s as keyof typeof counts] > 0)
      .map((s) => `${counts[s as keyof typeof counts]} ${s}`)
      .join(", ");
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">Vendor audit cross-check</h1>

      {departmentFilter && (
        <GlassPanel className="flex items-center justify-between gap-4">
          <p className="text-sm">
            Showing vendor categories owned by <strong>{DEPARTMENT_LABELS[departmentFilter] ?? departmentFilter}</strong>.
          </p>
          <button
            type="button"
            onClick={() => setSearchParams({})}
            className="text-xs underline"
            style={{ color: "var(--text-muted)" }}
          >
            Show all departments
          </button>
        </GlassPanel>
      )}

      <div className="flex gap-4 text-sm">
        <select
          className="rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
          value={vendorCategoryFilter}
          onChange={(e) => setVendorCategoryFilter(e.target.value)}
        >
          <option value="">All vendor categories</option>
          {(categoriesForDepartment ?? Object.keys(VENDOR_CATEGORY_LABELS)).map((value) => (
            <option key={value} value={value}>
              {VENDOR_CATEGORY_LABELS[value]}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
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

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading vendor audit reports...</p>}
      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {!loading && !error && documents.length === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>
            No vendor audit reports uploaded yet. Upload one as a "Vendor audit report" from the Upload page.
          </p>
        </GlassPanel>
      )}
      {!loading && !error && documents.length > 0 && visibleDocuments.length === 0 && (
        <GlassPanel>
          <p style={{ color: "var(--text-muted)" }}>No documents match this vendor category.</p>
        </GlassPanel>
      )}

      {visibleDocuments.map((document) => {
        const rows = findingsByDocument.get(document.id) ?? [];
        const isProcessed = document.status === "processed";
        return (
          <div key={document.id} className="flex flex-col gap-2">
            <div className="flex items-end justify-between gap-4">
              <h2 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
                {document.title} — {categoryLabel(document.vendor_category)}
                {rows.length > 0 && ` — ${summarize(rows)}`}
              </h2>
              {isProcessed ? (
                <button
                  type="button"
                  onClick={() => handleRun(document.id)}
                  disabled={runningId === document.id}
                  className="rounded-lg border px-3 py-1 text-xs font-medium"
                  style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
                >
                  {runningId === document.id ? "Running..." : "Run cross-check"}
                </button>
              ) : (
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {document.status === "failed"
                    ? `Processing failed: ${document.processing_error}`
                    : `Waiting to be processed (${document.status})`}
                </span>
              )}
            </div>

            {rows.length === 0 && isProcessed && (
              <GlassPanel>
                <p style={{ color: "var(--text-muted)" }}>Not run yet. Click "Run cross-check" above.</p>
              </GlassPanel>
            )}

            {rows.map((finding) => (
              <GlassPanel key={finding.id} className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {finding.standard.citation}
                  </div>
                  <div className="mt-1 font-medium">
                    {finding.standard.requirement_name}
                    <span className="ml-2 text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                      {finding.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm">{finding.explanation}</p>
                </div>
                <SeverityChip severity={finding.severity} />
              </GlassPanel>
            ))}
          </div>
        );
      })}
    </div>
  );
}
