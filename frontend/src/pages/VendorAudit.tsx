import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import {
  CheckHeader,
  EmptyState,
  FilterChips,
  GroupCard,
  ResultRow,
  StatCards,
  type StatusDef,
} from "../components/CheckResults";
import { countBy } from "../countBy";
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

const STATUSES: StatusDef[] = [
  { value: "missing", label: "Missing", tone: "bad" },
  { value: "partial", label: "Partial", tone: "warn" },
  { value: "satisfied", label: "Satisfied", tone: "good" },
];
const STATUS_BY_VALUE = Object.fromEntries(STATUSES.map((s) => [s.value, s]));

/** "VEN-RM-2026-008_Acme_Excipient_Supplier_Audit_Report.docx" →
 * "VEN-RM-2026-008 Acme Excipient Supplier Audit Report" */
function displayTitle(filename: string): string {
  return filename.replace(/\.(docx|pdf|txt)$/i, "").replace(/_/g, " ");
}

export function VendorAudit() {
  const [searchParams, setSearchParams] = useSearchParams();
  const departmentFilter = searchParams.get("department");

  const [documents, setDocuments] = useState<VendorDocumentOut[]>([]);
  const [findings, setFindings] = useState<VendorAuditFindingOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [vendorCategoryFilter, setVendorCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const loadAll = () => {
    setLoading(true);
    return Promise.all([
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

  useEffect(() => {
    loadAll();
  }, []);

  const handleRun = async (documentId: string) => {
    setRunningId(documentId);
    setError(null);
    try {
      await api.post(`/vendor-audit/${documentId}/run`);
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
    } finally {
      setRunningId(null);
    }
  };

  // A ?department= link (from the Checklist page) narrows to the vendor
  // categories that department owns.
  const allowedCategories = useMemo(
    () => (departmentFilter ? VENDOR_CATEGORIES_BY_DEPARTMENT[departmentFilter] ?? [] : null),
    [departmentFilter],
  );
  const inScopeDocuments = useMemo(
    () => documents.filter((d) => !allowedCategories || (d.vendor_category && allowedCategories.includes(d.vendor_category))),
    [documents, allowedCategories],
  );
  const visibleDocuments = useMemo(
    () => inScopeDocuments.filter((d) => !vendorCategoryFilter || d.vendor_category === vendorCategoryFilter),
    [inScopeDocuments, vendorCategoryFilter],
  );

  const findingsByDocument = useMemo(() => {
    const map = new Map<string, VendorAuditFindingOut[]>();
    for (const f of findings) {
      if (!map.has(f.document.id)) map.set(f.document.id, []);
      map.get(f.document.id)!.push(f);
    }
    return map;
  }, [findings]);

  // Stats cover the visible documents; the status filter only narrows rows.
  const visibleFindings = useMemo(
    () => visibleDocuments.flatMap((d) => findingsByDocument.get(d.id) ?? []),
    [visibleDocuments, findingsByDocument],
  );
  const counts = useMemo(() => countBy(visibleFindings, (f) => f.status), [visibleFindings]);
  const categoryCounts = countBy(inScopeDocuments, (d) => d.vendor_category ?? "");
  const reportsRun = visibleDocuments.filter((d) => findingsByDocument.has(d.id)).length;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <CheckHeader
        eyebrow="Verification check"
        title="Vendor audit cross-check"
        description="Reads each supplier's audit report and checks it against the standards for that vendor category, so you can see what the vendor actually demonstrated, not just that a report exists."
        meta={
          visibleDocuments.length > 0
            ? `${reportsRun} of ${visibleDocuments.length} report${visibleDocuments.length === 1 ? "" : "s"} cross-checked`
            : undefined
        }
      />

      {departmentFilter && (
        <div className="card flex items-center justify-between gap-4 px-5 py-3 text-sm">
          <p>
            Showing vendors owned by <strong>{DEPARTMENT_LABELS[departmentFilter] ?? departmentFilter}</strong>
          </p>
          <button type="button" onClick={() => setSearchParams({})} className="btn-secondary px-3 py-1.5 text-xs">
            Show all departments
          </button>
        </div>
      )}

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}
      {loading && documents.length === 0 && <p style={{ color: "var(--text-muted)" }}>Loading vendor audit reports...</p>}

      {!loading && inScopeDocuments.length === 0 && (
        <EmptyState
          title="No vendor audit reports yet"
          body="Upload a supplier's audit report as type “Vendor audit report” and pick its vendor category. It will appear here, ready to cross-check."
          actionLabel="Upload a report"
          actionTo="/upload"
        />
      )}

      {inScopeDocuments.length > 0 && (
        <>
          {visibleFindings.length > 0 && (
            <StatCards scoreLabel="Vendor standards met" statuses={STATUSES} counts={counts} active={statusFilter} onSelect={setStatusFilter} />
          )}

          <FilterChips
            allLabel="All vendor categories"
            value={vendorCategoryFilter}
            onChange={setVendorCategoryFilter}
            options={Object.keys(VENDOR_CATEGORY_LABELS)
              .filter((c) => categoryCounts[c])
              .map((c) => ({ value: c, label: VENDOR_CATEGORY_LABELS[c], count: categoryCounts[c] }))}
          />

          {visibleDocuments.map((document) => {
            const all = findingsByDocument.get(document.id) ?? [];
            const shown = all.filter((f) => !statusFilter || f.status === statusFilter);
            const isProcessed = document.status === "processed";
            const hasRun = all.length > 0;
            const isRunning = runningId === document.id;

            // With a status filter on, hide reports that have nothing to show for it.
            if (statusFilter && hasRun && shown.length === 0) return null;

            return (
              <GroupCard
                key={document.id}
                title={displayTitle(document.title)}
                badge={
                  document.vendor_category && (
                    <span
                      className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                      style={{ background: "var(--tint-violet)", color: "#6d28d9" }}
                    >
                      {VENDOR_CATEGORY_LABELS[document.vendor_category] ?? document.vendor_category}
                    </span>
                  )
                }
                subtitle={
                  !isProcessed
                    ? document.status === "failed"
                      ? `Processing failed: ${document.processing_error}`
                      : `Waiting to be processed (${document.status})`
                    : hasRun
                      ? `${all.length} standard${all.length === 1 ? "" : "s"} checked`
                      : "Not cross-checked yet"
                }
                statuses={STATUSES}
                counts={countBy(all, (f) => f.status)}
                action={
                  isProcessed && (
                    <button
                      type="button"
                      onClick={() => handleRun(document.id)}
                      disabled={isRunning}
                      className={`${hasRun ? "btn-secondary" : "btn-primary"} px-4 py-2 text-sm`}
                    >
                      {isRunning ? "Running..." : hasRun ? "Run again" : "Run cross-check"}
                    </button>
                  )
                }
              >
                {shown.map((f) => (
                  <ResultRow
                    key={f.id}
                    status={STATUS_BY_VALUE[f.status]}
                    title={f.standard.requirement_name}
                    citation={f.standard.citation}
                    explanation={f.explanation}
                  />
                ))}
              </GroupCard>
            );
          })}
        </>
      )}
    </div>
  );
}
