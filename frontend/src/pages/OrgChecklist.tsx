import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { api, ApiError } from "../api/client";
import { CHECKLIST_DEPARTMENTS, type EffectiveChecklistItem } from "../checklistDepartments";
import { useOnboarding } from "../context/OnboardingContext";

const muted = { color: "var(--text-muted)" };

/** Department checklist overview: one box per department. Clicking a box
 * opens that department's checklist items on their own page
 * (/org-checklist/:department). */
export function OrgChecklist() {
  // Set when onboarding has just finished, for a one-time welcome note.
  // Captured once into local state, then cleared in the context so a later
  // visit doesn't show it (survives StrictMode's dev double-mount).
  const { justCompleted, clearJustCompleted } = useOnboarding();
  const [welcome] = useState(justCompleted);
  useEffect(() => clearJustCompleted(), [clearJustCompleted]);

  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<EffectiveChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<EffectiveChecklistItem[]>("/audit-simulation/checklist")
      .then(setItems)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load checklist."))
      .finally(() => setLoading(false));
  }, []);

  const byDepartment = useMemo(() => {
    const map = new Map<string, EffectiveChecklistItem[]>();
    for (const item of items) {
      if (!map.has(item.department)) map.set(item.department, []);
      map.get(item.department)!.push(item);
    }
    return map;
  }, [items]);

  // Older links used ?dept=qa on this page; send them to the department page.
  const legacyDept = searchParams.get("dept");
  if (legacyDept && CHECKLIST_DEPARTMENTS.some((d) => d.value === legacyDept)) {
    return <Navigate to={`/org-checklist/${legacyDept}`} replace />;
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <p className="eyebrow">Internal audit</p>
        <h1 className="mt-2 text-3xl font-bold">Department checklist</h1>
        <p className="mt-2 max-w-3xl" style={muted}>
          The required records the internal audit simulation checks for. Open a department to turn off items that
          don't apply to your site, or add your own.
        </p>
      </div>

      {welcome && (
        <GlassPanel className="!p-5">
          <p className="font-semibold">You're all set.</p>
          <p className="mt-1 text-sm" style={muted}>
            {welcome.itemsAdded
              ? `Added ${welcome.itemsAdded} item${welcome.itemsAdded === 1 ? "" : "s"} from your template to this checklist. `
              : "You're starting from the standard checklist. "}
            Next,{" "}
            <Link to="/audit-simulation/new" className="underline">
              start an internal audit simulation
            </Link>
            .
          </p>
        </GlassPanel>
      )}

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CHECKLIST_DEPARTMENTS.map((d) => {
          const deptItems = byDepartment.get(d.value) ?? [];
          const active = deptItems.filter((i) => !i.is_excluded).length;
          const off = deptItems.filter((i) => i.is_excluded).length;
          const custom = deptItems.filter((i) => i.is_custom).length;
          return (
            <Link
              key={d.value}
              to={`/org-checklist/${d.value}`}
              className="card flex flex-col p-5 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start gap-3">
                <span
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
                  style={{ background: d.tint }}
                >
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={d.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d={d.icon} />
                  </svg>
                </span>
                <div className="min-w-0">
                  {d.label !== d.name && (
                    <p className="text-xs font-semibold" style={muted}>
                      {d.label}
                    </p>
                  )}
                  <h2 className="text-lg font-semibold">{d.name}</h2>
                  <p className="mt-0.5 text-sm" style={muted}>
                    {d.blurb}
                  </p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 border-t pt-4" style={{ borderColor: "var(--glass-border)" }}>
                <TileStat label="Active" value={loading ? "–" : active} />
                <TileStat label="Off" value={loading ? "–" : off} />
                <TileStat label="Custom" value={loading ? "–" : custom} />
              </div>
              <span className="mt-4 text-sm font-medium" style={{ color: "var(--brand-blue-text)" }}>
                Open checklist →
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function TileStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-xs" style={muted}>
        {label}
      </p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}
