import { AUDIT_TYPES, DEPARTMENTS, type SimulationRunSummary } from "../simulationRuns";
import type { AuditFilterState } from "../auditFilters";

/** Filter panel for the All audits and Generate report pages (state and
 * matching logic live in src/auditFilters.ts). */

const INPUT = "mt-1.5 w-full rounded-lg border px-3 py-2 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)", color: "var(--text)" };
const muted = { color: "var(--text-muted)" };

export function AuditFilterPanel({
  filters: f,
  runs,
  showStatus = false,
}: {
  filters: AuditFilterState;
  runs: SimulationRunSummary[];
  showStatus?: boolean;
}) {
  // Lead auditors seen across audits, for the filter list.
  const leadMap = new Map<string, string>();
  for (const r of runs) if (r.lead_employee_id) leadMap.set(r.lead_employee_id, `${r.lead_name} (${r.lead_employee_id})`);
  const leads = [...leadMap.entries()].sort((a, b) => a[1].localeCompare(b[1]));

  return (
    <aside className="card h-fit p-5 lg:sticky lg:top-28">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Filters</h2>
        {f.active && (
          <button type="button" onClick={f.clear} className="text-xs font-medium underline" style={{ color: "var(--brand-blue-text)" }}>
            Clear all
          </button>
        )}
      </div>
      <div className="mt-4 flex flex-col gap-4">
        <label className="text-xs font-medium" style={muted}>
          Search
          <input
            className={INPUT}
            style={INPUT_STYLE}
            value={f.q}
            onChange={(e) => f.set("q", e.target.value)}
            placeholder="Audit name, SIM ID, lead..."
          />
        </label>
        {showStatus && (
          <label className="text-xs font-medium" style={muted}>
            Status
            <select className={INPUT} style={INPUT_STYLE} value={f.status} onChange={(e) => f.set("status", e.target.value)}>
              <option value="">Any status</option>
              <option value="completed">Completed</option>
              <option value="draft">Draft (not run yet)</option>
            </select>
          </label>
        )}
        <label className="text-xs font-medium" style={muted}>
          Audit type
          <select className={INPUT} style={INPUT_STYLE} value={f.type} onChange={(e) => f.set("type", e.target.value)}>
            <option value="">Any type</option>
            {AUDIT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-medium" style={muted}>
          Lead auditor
          <select className={INPUT} style={INPUT_STYLE} value={f.lead} onChange={(e) => f.set("lead", e.target.value)}>
            <option value="">Anyone</option>
            {leads.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <div>
          <p className="text-xs font-medium" style={muted}>
            Covers departments
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {DEPARTMENTS.map((d) => {
              const on = f.depts.includes(d.value);
              return (
                <button
                  key={d.value}
                  type="button"
                  aria-pressed={on}
                  onClick={() => f.toggleDept(d.value)}
                  className="rounded-full border px-3 py-1 text-xs font-medium"
                  style={
                    on
                      ? { background: "var(--tint-blue)", borderColor: "var(--brand-blue)", color: "var(--brand-blue-text)" }
                      : { background: "#fff", borderColor: "var(--glass-border)", color: "#4b5563" }
                  }
                >
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs font-medium" style={muted}>
            From
            <input type="date" className={INPUT} style={INPUT_STYLE} value={f.from} onChange={(e) => f.set("from", e.target.value)} />
          </label>
          <label className="text-xs font-medium" style={muted}>
            To
            <input type="date" className={INPUT} style={INPUT_STYLE} value={f.to} onChange={(e) => f.set("to", e.target.value)} />
          </label>
        </div>
      </div>
    </aside>
  );
}
