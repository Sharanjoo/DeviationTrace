import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { CHECKLIST_DEPARTMENTS, type EffectiveChecklistItem } from "../checklistDepartments";
import { VENDOR_CATEGORIES_BY_DEPARTMENT, VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";

const EMPTY_FORM = { item_name: "", citation: "", requirement_text: "", match_phrases: "" };
const muted = { color: "var(--text-muted)" };

/** One department's checklist items (/org-checklist/:department): turn
 * standard items off or back on, and add or delete the org's own items. */
export function DepartmentChecklist() {
  const { department } = useParams<{ department: string }>();
  const dept = CHECKLIST_DEPARTMENTS.find((d) => d.value === department) ?? null;

  const [rows, setRows] = useState<EffectiveChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(
    () =>
      api
        .get<EffectiveChecklistItem[]>("/audit-simulation/checklist")
        .then((all) => setRows(all.filter((i) => i.department === department)))
        .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load checklist."))
        .finally(() => setLoading(false)),
    [department],
  );

  useEffect(() => {
    load();
  }, [load]);

  if (!dept) {
    return (
      <GlassPanel className="mx-auto max-w-xl">
        <p className="font-semibold">Unknown department.</p>
        <Link to="/org-checklist" className="mt-2 inline-block text-sm underline">
          Back to the department checklist
        </Link>
      </GlassPanel>
    );
  }

  const toggleExclusion = async (item: EffectiveChecklistItem) => {
    setBusyId(item.id);
    setError(null);
    try {
      if (item.is_excluded) {
        await api.del(`/audit-simulation/checklist/${item.id}/exclude`);
      } else {
        await api.post(`/audit-simulation/checklist/${item.id}/exclude`);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed.");
    } finally {
      setBusyId(null);
    }
  };

  const deleteCustomItem = async (id: string) => {
    setBusyId(id);
    setError(null);
    try {
      await api.del(`/audit-simulation/checklist/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
    } finally {
      setBusyId(null);
    }
  };

  const submitCustomItem = async () => {
    if (!form.item_name.trim() || !form.citation.trim() || !form.requirement_text.trim()) {
      setError("Item name, citation, and requirement text are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/audit-simulation/checklist", {
        department: dept.value,
        item_name: form.item_name.trim(),
        citation: form.citation.trim(),
        requirement_text: form.requirement_text.trim(),
        match_phrases: form.match_phrases
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean),
      });
      setForm(EMPTY_FORM);
      setAdding(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add item.");
    } finally {
      setSubmitting(false);
    }
  };

  const vendorCategories = VENDOR_CATEGORIES_BY_DEPARTMENT[dept.value] ?? [];
  const activeCount = rows.filter((i) => !i.is_excluded).length;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <Link to="/org-checklist" className="text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
        ← All departments
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl" style={{ background: dept.tint }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={dept.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d={dept.icon} />
            </svg>
          </span>
          <div>
            <p className="eyebrow">Department checklist</p>
            <h1 className="mt-1 text-3xl font-bold">{dept.name}</h1>
            <p className="mt-1 text-sm" style={muted}>
              {loading ? "Loading..." : `${activeCount} of ${rows.length} item${rows.length === 1 ? "" : "s"} active`}
              {vendorCategories.length > 0 && (
                <>
                  {" · Also audits vendors: "}
                  {vendorCategories.map((cat, i) => (
                    <span key={cat}>
                      <Link to={`/vendor-audit?department=${dept.value}`} className="underline">
                        {VENDOR_CATEGORY_LABELS[cat] ?? cat}
                      </Link>
                      {i < vendorCategories.length - 1 ? ", " : ""}
                    </span>
                  ))}
                </>
              )}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            setAdding(!adding);
            setForm(EMPTY_FORM);
          }}
          className={adding ? "btn-secondary px-4 py-2 text-sm" : "btn-primary px-4 py-2 text-sm"}
        >
          {adding ? "Cancel" : "Add item"}
        </button>
      </div>

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {adding && (
        <GlassPanel className="flex flex-col gap-2">
          <p className="text-sm font-semibold">New {dept.name} item</p>
          <input
            className="rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--glass-border)" }}
            placeholder="Item name"
            value={form.item_name}
            onChange={(e) => setForm({ ...form, item_name: e.target.value })}
          />
          <input
            className="rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--glass-border)" }}
            placeholder="Citation (e.g. Company SOP-XX-001)"
            value={form.citation}
            onChange={(e) => setForm({ ...form, citation: e.target.value })}
          />
          <textarea
            className="rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--glass-border)" }}
            placeholder="Requirement text"
            rows={2}
            value={form.requirement_text}
            onChange={(e) => setForm({ ...form, requirement_text: e.target.value })}
          />
          <input
            className="rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--glass-border)" }}
            placeholder="Match phrases, comma-separated (e.g. microbial limit test)"
            value={form.match_phrases}
            onChange={(e) => setForm({ ...form, match_phrases: e.target.value })}
          />
          <button
            type="button"
            disabled={submitting}
            onClick={submitCustomItem}
            className="self-start btn-primary px-4 py-2 text-sm"
          >
            {submitting ? "Adding..." : "Add to checklist"}
          </button>
        </GlassPanel>
      )}

      {!loading && rows.length === 0 && (
        <GlassPanel>
          <p className="text-sm" style={muted}>
            No checklist items for {dept.name} yet. Use “Add item” to create one.
          </p>
        </GlassPanel>
      )}

      {rows.map((item) => (
        <GlassPanel key={item.id} className="flex items-start justify-between gap-4">
          {/* Only the text fades for an excluded item; its Include button stays prominent. */}
          <div className={item.is_excluded ? "opacity-50" : ""}>
            <div className="text-xs" style={muted}>
              {item.citation}
              {item.is_custom && <span className="ml-2 font-semibold">CUSTOM</span>}
              {item.is_excluded && <span className="ml-2 font-semibold">EXCLUDED</span>}
            </div>
            <div className="mt-1 font-medium">{item.item_name}</div>
            <p className="mt-2 text-sm" style={muted}>
              {item.requirement_text}
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-2">
            {item.is_custom ? (
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => deleteCustomItem(item.id)}
                className="rounded-lg border px-3 py-1 text-xs"
                style={{ borderColor: "var(--glass-border)" }}
              >
                {busyId === item.id ? "Deleting..." : "Delete"}
              </button>
            ) : (
              <button
                type="button"
                disabled={busyId === item.id}
                onClick={() => toggleExclusion(item)}
                className={item.is_excluded ? "btn-primary px-3.5 py-1.5 text-xs" : "rounded-lg border px-3 py-1 text-xs"}
                style={item.is_excluded ? undefined : { borderColor: "var(--glass-border)" }}
              >
                {busyId === item.id ? "Saving..." : item.is_excluded ? "Include" : "Exclude"}
              </button>
            )}
          </div>
        </GlassPanel>
      ))}
    </div>
  );
}
