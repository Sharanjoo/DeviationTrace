import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { DEPARTMENT_LABELS, VENDOR_CATEGORIES_BY_DEPARTMENT, VENDOR_CATEGORY_LABELS } from "../departmentVendorMap";

interface EffectiveChecklistItem {
  id: string;
  department: string;
  item_name: string;
  citation: string;
  requirement_text: string;
  match_phrases: string[];
  is_custom: boolean;
  is_excluded: boolean;
}

const DEPARTMENTS = ["qc", "qa", "utilities", "manufacturing", "engineering"];

const EMPTY_FORM = { item_name: "", citation: "", requirement_text: "", match_phrases: "" };

export function OrgChecklist() {
  const [items, setItems] = useState<EffectiveChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [addingFor, setAddingFor] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get<EffectiveChecklistItem[]>("/audit-simulation/checklist")
      .then(setItems)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load checklist."))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const byDepartment = useMemo(() => {
    const map = new Map<string, EffectiveChecklistItem[]>();
    for (const item of items) {
      if (!map.has(item.department)) map.set(item.department, []);
      map.get(item.department)!.push(item);
    }
    return map;
  }, [items]);

  const toggleExclusion = async (item: EffectiveChecklistItem) => {
    setBusyId(item.id);
    setError(null);
    try {
      if (item.is_excluded) {
        await api.del(`/audit-simulation/checklist/${item.id}/exclude`);
      } else {
        await api.post(`/audit-simulation/checklist/${item.id}/exclude`);
      }
      load();
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
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
    } finally {
      setBusyId(null);
    }
  };

  const submitCustomItem = async (department: string) => {
    if (!form.item_name.trim() || !form.citation.trim() || !form.requirement_text.trim()) {
      setError("Item name, citation, and requirement text are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/audit-simulation/checklist", {
        department,
        item_name: form.item_name.trim(),
        citation: form.citation.trim(),
        requirement_text: form.requirement_text.trim(),
        match_phrases: form.match_phrases
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean),
      });
      setForm(EMPTY_FORM);
      setAddingFor(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add item.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">Your department checklist</h1>
      <p style={{ color: "var(--text-muted)" }}>
        This is the checklist Internal Audit Simulation actually runs against for your org. Turn off items that
        don't apply to your site, and add your own — department by department.
      </p>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading your checklist...</p>}
      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      {DEPARTMENTS.map((department) => {
        const rows = byDepartment.get(department) ?? [];
        const vendorCategories = VENDOR_CATEGORIES_BY_DEPARTMENT[department] ?? [];
        return (
          <div key={department} className="flex flex-col gap-2">
            <div className="flex items-end justify-between gap-4">
              <h2 className="text-lg font-semibold">{DEPARTMENT_LABELS[department]}</h2>
              <button
                type="button"
                onClick={() => {
                  setAddingFor(addingFor === department ? null : department);
                  setForm(EMPTY_FORM);
                }}
                className="rounded-lg border px-3 py-1 text-xs font-medium"
                style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
              >
                {addingFor === department ? "Cancel" : "Add item"}
              </button>
            </div>

            {vendorCategories.length > 0 && (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Also audits vendors:{" "}
                {vendorCategories.map((cat, i) => (
                  <span key={cat}>
                    <Link to={`/vendor-audit?department=${department}`} className="underline">
                      {VENDOR_CATEGORY_LABELS[cat] ?? cat}
                    </Link>
                    {i < vendorCategories.length - 1 ? ", " : ""}
                  </span>
                ))}
              </p>
            )}

            {addingFor === department && (
              <GlassPanel className="flex flex-col gap-2">
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
                  onClick={() => submitCustomItem(department)}
                  className="self-start rounded-lg border px-4 py-2 text-sm font-medium"
                  style={{ borderColor: "var(--glass-border)", background: "var(--surface-bg)", color: "var(--surface-text)" }}
                >
                  {submitting ? "Adding..." : "Add to checklist"}
                </button>
              </GlassPanel>
            )}

            {rows.map((item) => (
              <GlassPanel
                key={item.id}
                className={`flex items-start justify-between gap-4 ${item.is_excluded ? "opacity-50" : ""}`}
              >
                <div>
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {item.citation}
                    {item.is_custom && <span className="ml-2 font-semibold">CUSTOM</span>}
                    {item.is_excluded && <span className="ml-2 font-semibold">EXCLUDED</span>}
                  </div>
                  <div className="mt-1 font-medium">{item.item_name}</div>
                  <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
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
                      Delete
                    </button>
                  ) : (
                    <button
                      type="button"
                      disabled={busyId === item.id}
                      onClick={() => toggleExclusion(item)}
                      className="rounded-lg border px-3 py-1 text-xs"
                      style={{ borderColor: "var(--glass-border)" }}
                    >
                      {item.is_excluded ? "Include" : "Exclude"}
                    </button>
                  )}
                </div>
              </GlassPanel>
            ))}
          </div>
        );
      })}
    </div>
  );
}
