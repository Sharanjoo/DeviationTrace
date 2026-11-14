import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { AuditStepper } from "../components/AuditStepper";
import {
  AUDIT_TYPES,
  DEPARTMENTS,
  type AuditDetails,
  type DepartmentContact,
  type SimulationRunDetail,
} from "../simulationRuns";

const EMPTY: AuditDetails = {
  title: "",
  audit_type: "internal_audit",
  planned_date: null,
  lead_name: "",
  lead_employee_id: "",
  lead_title: null,
  lead_email: null,
  objective: null,
  departments: DEPARTMENTS.map((d) => d.value),
  department_contacts: [],
};

const INPUT = "mt-1.5 w-full rounded-lg border px-3.5 py-2.5 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)" };

function Field({ label, required, hint, children }: { label: string; required?: boolean; hint?: string; children: ReactNode }) {
  return (
    <label className="block text-sm font-medium">
      {label}
      {required && <span style={{ color: "var(--severity-critical)" }}> *</span>}
      {children}
      {hint && (
        <span className="mt-1 block text-xs font-normal" style={{ color: "var(--text-muted)" }}>
          {hint}
        </span>
      )}
    </label>
  );
}

function Section({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="card p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
        {description}
      </p>
      <div className="mt-5">{children}</div>
    </section>
  );
}

/** Step 1 of a new internal audit simulation: who, what, and which
 * departments. Also used to edit a draft's details (/runs/:runId/edit). */
export function NewAudit() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const editing = Boolean(runId);
  const [form, setForm] = useState<AuditDetails>(EMPTY);
  const [runCode, setRunCode] = useState<string | undefined>();
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    api
      .get<SimulationRunDetail>(`/audit-simulation/runs/${runId}`)
      .then((run) => {
        if (run.status !== "draft") {
          navigate(`/audit-simulation/runs/${run.id}`, { replace: true });
          return;
        }
        setRunCode(run.run_code);
        setForm({
          title: run.title ?? "",
          audit_type: run.audit_type ?? "internal_audit",
          planned_date: run.planned_date,
          lead_name: run.lead_name ?? "",
          lead_employee_id: run.lead_employee_id ?? "",
          lead_title: run.lead_title,
          lead_email: run.lead_email,
          objective: run.objective,
          departments: run.departments ?? DEPARTMENTS.map((d) => d.value),
          department_contacts: run.department_contacts ?? [],
        });
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load this audit."))
      .finally(() => setLoading(false));
  }, [runId, navigate]);

  const set = <K extends keyof AuditDetails>(key: K, value: AuditDetails[K]) => setForm((f) => ({ ...f, [key]: value }));

  const toggleDepartment = (value: string) =>
    setForm((f) => ({
      ...f,
      departments: f.departments.includes(value) ? f.departments.filter((d) => d !== value) : [...f.departments, value],
    }));

  const contactFor = (department: string): DepartmentContact =>
    form.department_contacts.find((c) => c.department === department) ?? { department, name: "", employee_id: "" };

  const setContact = (department: string, key: "name" | "employee_id", value: string) =>
    setForm((f) => {
      const others = f.department_contacts.filter((c) => c.department !== department);
      return { ...f, department_contacts: [...others, { ...contactFor(department), [key]: value }] };
    });

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (form.departments.length === 0) {
      setError("Pick at least one department to audit.");
      return;
    }
    setSaving(true);
    const payload = {
      ...form,
      planned_date: form.planned_date || null,
      // Only send contacts for departments still in scope.
      department_contacts: form.department_contacts.filter((c) => form.departments.includes(c.department)),
    };
    try {
      const run = editing
        ? await api.patch<SimulationRunDetail>(`/audit-simulation/runs/${runId}`, payload)
        : await api.post<SimulationRunDetail>("/audit-simulation/audits", payload);
      navigate(`/audit-simulation/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? readableError(err.message) : "Failed to save audit details.");
      setSaving(false);
    }
  };

  if (loading) return <p className="text-center" style={{ color: "var(--text-muted)" }}>Loading...</p>;

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl flex-col gap-6">
      <AuditStepper current={0} runCode={runCode} />
      <div>
        <p className="eyebrow">Internal audit simulation</p>
        <h1 className="mt-2 text-3xl font-bold">{editing ? "Edit audit details" : "Start a new audit simulation"}</h1>
        <p className="mt-2" style={{ color: "var(--text-muted)" }}>
          Tell us about the audit you're preparing for. These details go on the run and its report, so it's clear
          who ran it and what was in scope. Next you'll upload each department's documents.
        </p>
      </div>

      <Section title="About this audit" description="What you're preparing for, and when.">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Field label="Audit name" required>
              <input
                className={INPUT}
                style={INPUT_STYLE}
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder="e.g. Q4 2026 internal audit"
                required
                maxLength={255}
              />
            </Field>
          </div>
          <Field label="Audit type" required>
            <select className={INPUT} style={INPUT_STYLE} value={form.audit_type} onChange={(e) => set("audit_type", e.target.value)}>
              {AUDIT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Planned audit date" hint="When the real audit or inspection is expected.">
            <input
              type="date"
              className={INPUT}
              style={INPUT_STYLE}
              value={form.planned_date ?? ""}
              onChange={(e) => set("planned_date", e.target.value || null)}
            />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Objective / notes">
              <textarea
                className={INPUT}
                style={INPUT_STYLE}
                rows={3}
                value={form.objective ?? ""}
                onChange={(e) => set("objective", e.target.value)}
                placeholder="e.g. Confirm all departments are ready for the ISO 13485 surveillance audit."
              />
            </Field>
          </div>
        </div>
      </Section>

      <Section title="Lead auditor" description="The person in charge of this audit, who signs off on the results.">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" required>
            <input
              className={INPUT}
              style={INPUT_STYLE}
              value={form.lead_name}
              onChange={(e) => set("lead_name", e.target.value)}
              required
              maxLength={255}
              autoComplete="off"
            />
          </Field>
          <Field label="Employee ID" required>
            <input
              className={INPUT}
              style={INPUT_STYLE}
              value={form.lead_employee_id}
              onChange={(e) => set("lead_employee_id", e.target.value)}
              placeholder="e.g. EMP-1042"
              required
              maxLength={64}
              autoComplete="off"
            />
          </Field>
          <Field label="Job title">
            <input
              className={INPUT}
              style={INPUT_STYLE}
              value={form.lead_title ?? ""}
              onChange={(e) => set("lead_title", e.target.value)}
              placeholder="e.g. QA Manager"
              maxLength={255}
            />
          </Field>
          <Field label="Email">
            <input
              type="email"
              className={INPUT}
              style={INPUT_STYLE}
              value={form.lead_email ?? ""}
              onChange={(e) => set("lead_email", e.target.value)}
              autoComplete="off"
            />
          </Field>
        </div>
      </Section>

      <Section
        title="Departments in scope"
        description="Pick the departments this audit covers. Optionally name the person responsible for each one."
      >
        <div className="flex flex-col gap-3">
          {DEPARTMENTS.map((d) => {
            const checked = form.departments.includes(d.value);
            const contact = contactFor(d.value);
            return (
              <div
                key={d.value}
                className="rounded-xl border p-4 transition-colors"
                style={{
                  borderColor: checked ? "var(--brand-blue)" : "var(--glass-border)",
                  background: checked ? "var(--tint-blue)" : "#fff",
                }}
              >
                <label className="flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-blue-600"
                    checked={checked}
                    onChange={() => toggleDepartment(d.value)}
                  />
                  <span className="font-semibold">{d.name}</span>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {d.label}
                  </span>
                </label>
                {checked && (
                  <div className="mt-3 grid gap-3 pl-7 sm:grid-cols-2">
                    <Field label="Department owner">
                      <input
                        className={INPUT}
                        style={INPUT_STYLE}
                        value={contact.name}
                        onChange={(e) => setContact(d.value, "name", e.target.value)}
                        placeholder="Name"
                        autoComplete="off"
                      />
                    </Field>
                    <Field label="Owner's employee ID">
                      <input
                        className={INPUT}
                        style={INPUT_STYLE}
                        value={contact.employee_id}
                        onChange={(e) => setContact(d.value, "employee_id", e.target.value)}
                        placeholder="Employee ID"
                        autoComplete="off"
                      />
                    </Field>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Section>

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to={editing ? `/audit-simulation/runs/${runId}` : "/"}
          className="btn-secondary px-4 py-2.5 text-sm"
        >
          Cancel
        </Link>
        <button type="submit" disabled={saving} className="btn-primary px-5 py-2.5 text-sm">
          {saving ? "Saving..." : editing ? "Save details" : "Continue to documents →"}
        </button>
      </div>
    </form>
  );
}

/** FastAPI 422 bodies are JSON lists; show the first message plainly. */
function readableError(message: string): string {
  try {
    const body = JSON.parse(message);
    const first = Array.isArray(body.detail) ? body.detail[0] : null;
    if (first?.msg) {
      const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]).replace(/_/g, " ") : "";
      return field ? `${field}: ${first.msg}` : first.msg;
    }
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // not JSON
  }
  return message;
}
