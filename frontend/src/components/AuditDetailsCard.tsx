import type { ReactNode } from "react";
import {
  AUDIT_TYPE_LABELS,
  DEPARTMENT_NAMES,
  DEPARTMENTS,
  formatPlannedDate,
  type SimulationRunSummary,
} from "../simulationRuns";

/** The audit's details (what, who, scope) as entered in step 1. */
export function AuditDetailsCard({ run, action }: { run: SimulationRunSummary; action?: ReactNode }) {
  if (!run.title) return null;
  const departments = run.departments ?? DEPARTMENTS.map((d) => d.value);
  const contacts = new Map((run.department_contacts ?? []).map((c) => [c.department, c]));

  const fields: { label: string; value: ReactNode }[] = [
    { label: "Audit type", value: AUDIT_TYPE_LABELS[run.audit_type ?? ""] ?? run.audit_type },
    { label: "Planned date", value: run.planned_date ? formatPlannedDate(run.planned_date) : "Not set" },
    {
      label: "Lead auditor",
      value: (
        <>
          {run.lead_name}
          <span className="block text-xs font-normal" style={{ color: "var(--text-muted)" }}>
            ID {run.lead_employee_id}
            {run.lead_title && ` · ${run.lead_title}`}
          </span>
        </>
      ),
    },
  ];

  return (
    <section className="card p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Audit details</p>
          <h2 className="mt-1 text-xl font-semibold">{run.title}</h2>
        </div>
        {action}
      </div>
      <dl className="mt-4 grid gap-x-6 gap-y-4 sm:grid-cols-3">
        {fields.map((f) => (
          <div key={f.label}>
            <dt className="text-xs" style={{ color: "var(--text-muted)" }}>
              {f.label}
            </dt>
            <dd className="mt-0.5 font-semibold">{f.value}</dd>
          </div>
        ))}
      </dl>
      {run.objective && (
        <p className="mt-4 text-sm" style={{ color: "var(--text-muted)" }}>
          <span className="font-medium" style={{ color: "var(--text)" }}>
            Objective:
          </span>{" "}
          {run.objective}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {departments.map((d) => {
          const c = contacts.get(d);
          return (
            <span
              key={d}
              className="rounded-lg border px-3 py-1.5 text-xs"
              style={{ borderColor: "var(--glass-border)", background: "#fff" }}
            >
              <span className="font-semibold">{DEPARTMENT_NAMES[d] ?? d}</span>
              {c && (c.name || c.employee_id) && (
                <span style={{ color: "var(--text-muted)" }}>
                  {" "}
                  · {c.name}
                  {c.employee_id && ` (${c.employee_id})`}
                </span>
              )}
            </span>
          );
        })}
      </div>
    </section>
  );
}
