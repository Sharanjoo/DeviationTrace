import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { DEPARTMENT_LABELS, VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";

interface ScopeTemplateSummary {
  scope_category: string;
  industry: string;
  label: string;
  description: string;
}

interface ChecklistItemTemplate {
  department: string;
  item_name: string;
  citation: string;
  requirement_text: string;
}

interface VendorStandardTemplate {
  vendor_category: string;
  requirement_name: string;
  citation: string;
  requirement_text: string;
}

interface ScopeTemplateDetail extends ScopeTemplateSummary {
  source_note: string;
  checklist_items: ChecklistItemTemplate[];
  vendor_standards: VendorStandardTemplate[];
}

function groupBy<T, K extends string>(items: T[], key: (item: T) => K): [K, T[]][] {
  const map = new Map<K, T[]>();
  for (const item of items) {
    const k = key(item);
    if (!map.has(k)) map.set(k, []);
    map.get(k)!.push(item);
  }
  return Array.from(map.entries());
}

export function Onboarding() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<ScopeTemplateSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<ScopeTemplateDetail | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [adopting, setAdopting] = useState(false);
  const [adoptResult, setAdoptResult] = useState<{ added: number; skipped: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<ScopeTemplateSummary[]>("/onboarding/scope-templates")
      .then(setTemplates)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load scope templates."))
      .finally(() => setLoadingList(false));
  }, []);

  const handleSelect = (category: string) => {
    setSelected(category);
    setDetail(null);
    setAdoptResult(null);
    setLoadingDetail(true);
    setError(null);
    api
      .get<ScopeTemplateDetail>(`/onboarding/scope-templates/${category}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load skeleton."))
      .finally(() => setLoadingDetail(false));
  };

  const handleAdopt = async () => {
    if (!selected) return;
    setAdopting(true);
    setError(null);
    try {
      const result = await api.post<{ added: number; skipped: number }>(`/onboarding/scope-templates/${selected}/adopt`);
      setAdoptResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to adopt skeleton.");
    } finally {
      setAdopting(false);
    }
  };

  const checklistGroups = detail ? groupBy(detail.checklist_items, (i) => i.department) : [];
  const vendorGroups = detail ? groupBy(detail.vendor_standards, (s) => s.vendor_category) : [];

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-3xl font-bold">New company skeleton</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Tell us what you make and we'll show you the SOPs, reports, and records a comparable real manufacturer
        needed — modeled on a real audit or FDA warning letter, with citations, not generic boilerplate.
      </p>

      {loadingList && <p style={{ color: "var(--text-muted)" }}>Loading scope templates...</p>}
      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      <div className="flex flex-col gap-3 sm:flex-row">
        {templates.map((t) => (
          <button
            key={t.scope_category}
            type="button"
            onClick={() => handleSelect(t.scope_category)}
            className="flex-1 rounded-xl border p-4 text-left transition-colors"
            style={{
              borderColor: selected === t.scope_category ? "var(--accent, #3b82f6)" : "var(--glass-border)",
              background: "var(--surface-bg)",
              color: "var(--surface-text)",
            }}
          >
            <div className="text-xs uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
              {t.industry}
            </div>
            <div className="mt-1 font-semibold">{t.label}</div>
            <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
              {t.description}
            </p>
          </button>
        ))}
      </div>

      {loadingDetail && <p style={{ color: "var(--text-muted)" }}>Building skeleton...</p>}

      {detail && (
        <>
          <GlassPanel>
            <p className="text-sm">
              <strong>Source: </strong>
              {detail.source_note}
            </p>
          </GlassPanel>

          <div className="flex items-center justify-between gap-4">
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Ready to use this as your actual checklist? Adopting copies these items into your own,
              department-wise editable checklist.
            </p>
            <button
              type="button"
              onClick={handleAdopt}
              disabled={adopting}
              className="shrink-0 btn-primary px-4 py-2 text-sm"
            >
              {adopting ? "Adopting..." : "Adopt this as my checklist"}
            </button>
          </div>

          {adoptResult && (
            <GlassPanel>
              <p className="text-sm">
                Added {adoptResult.added} new item{adoptResult.added === 1 ? "" : "s"} to your checklist
                {adoptResult.skipped > 0 && ` (${adoptResult.skipped} already there)`}.{" "}
                <button type="button" onClick={() => navigate("/org-checklist")} className="underline">
                  Go to your checklist
                </button>
              </p>
            </GlassPanel>
          )}

          <h2 className="mt-4 text-lg font-semibold">Required documents by department</h2>
          {checklistGroups.map(([department, items]) => (
            <div key={department} className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
                {DEPARTMENT_LABELS[department] ?? department} — {items.length} items
              </h3>
              {items.map((item) => (
                <GlassPanel key={item.item_name}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="font-medium">{item.item_name}</div>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {item.citation}
                    </span>
                  </div>
                  <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    {item.requirement_text}
                  </p>
                </GlassPanel>
              ))}
            </div>
          ))}

          <h2 className="mt-4 text-lg font-semibold">Vendor audit standards by category</h2>
          {vendorGroups.map(([category, standards]) => (
            <div key={category} className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
                {VENDOR_CATEGORY_LABELS[category] ?? category} — {standards.length} items
              </h3>
              {standards.map((std) => (
                <GlassPanel key={std.requirement_name}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="font-medium">{std.requirement_name}</div>
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {std.citation}
                    </span>
                  </div>
                  <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                    {std.requirement_text}
                  </p>
                </GlassPanel>
              ))}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
