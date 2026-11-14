import { useSearchParams } from "react-router-dom";
import { runDate, type SimulationRunSummary } from "./simulationRuns";

/** Shared audit filters for the All audits and Generate report pages. The
 * fields mirror the details entered when starting a simulation. Values live
 * in the URL, so a filtered list survives a reload and can be shared.
 * The filter panel is components/AuditFilters.tsx. */

// Display name for runs made without audit details.
export const QUICK_RUN = "Quick run (all departments)";

/** "YYYY-MM-DD" in the viewer's time zone, to compare with date inputs. */
function localDay(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export interface AuditFilterState {
  q: string;
  type: string;
  lead: string;
  status: string;
  from: string;
  to: string;
  depts: string[];
  set: (key: string, value: string) => void;
  toggleDept: (value: string) => void;
  clear: () => void;
  active: boolean;
}

export function useAuditFilters(): AuditFilterState {
  const [params, setParams] = useSearchParams();
  const depts = (params.get("depts") ?? "").split(",").filter(Boolean);
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  const state = {
    q: params.get("q") ?? "",
    type: params.get("type") ?? "",
    lead: params.get("lead") ?? "",
    status: params.get("status") ?? "",
    from: params.get("from") ?? "",
    to: params.get("to") ?? "",
    depts,
  };
  return {
    ...state,
    set,
    toggleDept: (value) =>
      set("depts", (depts.includes(value) ? depts.filter((d) => d !== value) : [...depts, value]).join(",")),
    clear: () => setParams({}, { replace: true }),
    active: Boolean(state.q || state.type || state.lead || state.status || state.from || state.to || depts.length),
  };
}

export function applyAuditFilters(runs: SimulationRunSummary[], f: AuditFilterState): SimulationRunSummary[] {
  const needle = f.q.trim().toLowerCase();
  return runs.filter((r) => {
    if (needle) {
      const haystack = [r.run_code, r.title ?? QUICK_RUN, r.objective, r.lead_name, r.lead_employee_id]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    if (f.type && r.audit_type !== f.type) return false;
    if (f.lead && r.lead_employee_id !== f.lead) return false;
    if (f.status && r.status !== f.status) return false;
    // Audits with no department list covered every department.
    if (f.depts.length && !f.depts.every((d) => !r.departments || r.departments.includes(d))) return false;
    const day = localDay(runDate(r));
    if (f.from && day < f.from) return false;
    if (f.to && day > f.to) return false;
    return true;
  });
}
