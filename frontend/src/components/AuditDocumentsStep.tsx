import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { DEPARTMENTS, type SimulationRunDetail } from "../simulationRuns";
import { AuditDetailsCard } from "./AuditDetailsCard";
import { AuditStepper } from "./AuditStepper";
import { StatusIcon } from "./CheckResults";

interface ChecklistItem {
  id: string;
  department: string;
  item_name: string;
  citation: string;
  is_excluded: boolean;
}

/** What's being added. Records/reports are checked for existence and
 * completeness; SOPs and deviation reports are also checked for content
 * against the regulatory requirements for their topic. */
type DocKind = "report" | "sop" | "deviation";
const KIND_LABELS: Record<DocKind, string> = { report: "Record / report", sop: "SOP", deviation: "Deviation report" };
const TOPICS = [
  { value: "deviation_handling", label: "Deviation handling" },
  { value: "capa", label: "CAPA" },
];

interface DocumentOut {
  id: string;
  type: string;
  title: string;
  department: string | null;
  status: string;
  processing_error: string | null;
  uploaded_at: string;
}

interface UploadState {
  key: string;
  department: string;
  name: string;
  state: "uploading" | "processing" | "done" | "failed";
  error?: string;
}

function displayTitle(filename: string): string {
  return filename.replace(/\.(docx|pdf|txt)$/i, "").replace(/_/g, " ");
}

/** Step 2 of a new simulation: upload each in-scope department's reports,
 * then run the simulation. Uploads go straight in as department reports,
 * already processed, so there's no separate upload or processing page. */
export function AuditDocumentsStep({
  run,
  onExecuted,
}: {
  run: SimulationRunDetail;
  onExecuted: (run: SimulationRunDetail) => void;
}) {
  const navigate = useNavigate();
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [discarding, setDiscarding] = useState(false);

  const loadDocuments = useCallback(
    () =>
      api
        .get<DocumentOut[]>("/documents")
        .then((all) => setDocuments(all.filter((d) => d.department && ["report", "sop", "deviation"].includes(d.type)))),
    [],
  );

  useEffect(() => {
    Promise.all([api.get<ChecklistItem[]>("/audit-simulation/checklist").then(setChecklist), loadDocuments()]).catch(
      (err) => setError(err instanceof ApiError ? err.message : "Failed to load documents."),
    );
  }, [loadDocuments]);

  const departments = useMemo(
    () => DEPARTMENTS.filter((d) => !run.departments || run.departments.includes(d.value)),
    [run.departments],
  );
  const contacts = new Map((run.department_contacts ?? []).map((c) => [c.department, c]));

  const patchUpload = (key: string, patch: Partial<UploadState>) =>
    setUploads((list) => list.map((u) => (u.key === key ? { ...u, ...patch } : u)));

  const handleFiles = async (department: string, files: FileList | null, kind: DocKind, topic: string) => {
    if (!files || files.length === 0) return;
    const batch = Array.from(files).map((file) => ({
      file,
      state: {
        key: `${department}-${file.name}-${Date.now()}-${Math.random()}`,
        department,
        name: file.name,
        state: "uploading" as const,
      },
    }));
    setUploads((list) => [...list, ...batch.map((b) => b.state)]);

    // One at a time: processing is synchronous on the server and quick.
    for (const { file, state } of batch) {
      try {
        const form = new FormData();
        form.append("type", kind);
        // Records have no topic; SOPs and deviation reports are checked
        // against the requirements for the topic chosen.
        form.append("process_area", kind === "report" ? "general" : topic);
        form.append("department", department);
        form.append("file", file);
        const doc = await api.upload<DocumentOut>("/documents", form);
        patchUpload(state.key, { state: "processing" });
        const processed = await api.post<DocumentOut>(`/documents/${doc.id}/process`);
        patchUpload(
          state.key,
          processed.status === "processed"
            ? { state: "done" }
            : { state: "failed", error: processed.processing_error ?? "Processing failed" },
        );
      } catch (err) {
        patchUpload(state.key, { state: "failed", error: err instanceof ApiError ? err.message : "Upload failed" });
      }
    }
    await loadDocuments();
    // Finished uploads now appear in the documents list; keep only failures.
    setUploads((list) => list.filter((u) => u.state !== "done"));
  };

  const busy = uploads.some((u) => u.state === "uploading" || u.state === "processing");
  const inScopeDocs = documents.filter((d) => d.department && departments.some((x) => x.value === d.department));

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      onExecuted(await api.post<SimulationRunDetail>(`/audit-simulation/runs/${run.id}/execute`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Run failed.");
      setRunning(false);
    }
  };

  const handleDiscard = async () => {
    if (!window.confirm(`Discard ${run.run_code}? Its audit details are deleted; uploaded documents are kept.`)) return;
    setDiscarding(true);
    try {
      await api.del(`/audit-simulation/runs/${run.id}`);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to discard.");
      setDiscarding(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <AuditStepper current={1} runCode={run.run_code} />
      <div>
        <p className="eyebrow">Internal audit simulation</p>
        <h1 className="mt-2 text-3xl font-bold">Upload documents</h1>
        <p className="mt-2 max-w-3xl" style={{ color: "var(--text-muted)" }}>
          Add each department's records, SOPs and deviation reports. Records are checked for existence and completeness;
          SOPs and deviation reports are also read and checked against the regulatory requirements for their topic.
          Anything already on file counts too.
        </p>
      </div>

      <AuditDetailsCard
        run={run}
        action={
          <Link to={`/audit-simulation/runs/${run.id}/edit`} className="btn-secondary px-3 py-1.5 text-xs">
            Edit details
          </Link>
        }
      />

      {departments.map((d) => {
        const required = checklist.filter((i) => i.department === d.value && !i.is_excluded);
        const docs = documents.filter((doc) => doc.department === d.value);
        const pending = uploads.filter((u) => u.department === d.value);
        const owner = contacts.get(d.value);
        return (
          <DepartmentUploadCard
            key={d.value}
            name={d.name}
            owner={owner && (owner.name || owner.employee_id) ? `${owner.name}${owner.employee_id ? ` (${owner.employee_id})` : ""}` : null}
            required={required}
            docs={docs}
            pending={pending}
            onFiles={(files, kind, topic) => handleFiles(d.value, files, kind, topic)}
          />
        );
      })}

      {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

      <div className="card sticky bottom-4 flex items-center justify-between gap-3 px-4 py-3">
        <p className="hidden min-w-0 flex-1 truncate text-sm md:block" style={{ color: "var(--text-muted)" }}>
          <strong style={{ color: "var(--text)" }}>{inScopeDocs.length}</strong> document
          {inScopeDocs.length === 1 ? "" : "s"} on file across {departments.length} department
          {departments.length === 1 ? "" : "s"}
          {busy && " · uploading..."}
        </p>
        <div className="flex shrink-0 gap-2 max-md:w-full max-md:justify-between">
          <button type="button" onClick={handleDiscard} disabled={discarding || running} className="btn-secondary px-4 py-2 text-sm">
            Discard draft
          </button>
          <button type="button" onClick={handleRun} disabled={running || busy} className="btn-primary px-5 py-2 text-sm">
            {running ? "Running..." : `Run simulation ${run.run_code} →`}
          </button>
        </div>
      </div>
    </div>
  );
}

function DepartmentUploadCard({
  name,
  owner,
  required,
  docs,
  pending,
  onFiles,
}: {
  name: string;
  owner: string | null;
  required: ChecklistItem[];
  docs: DocumentOut[];
  pending: UploadState[];
  onFiles: (files: FileList | null, kind: DocKind, topic: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [kind, setKind] = useState<DocKind>("report");
  const [topic, setTopic] = useState("deviation_handling");

  return (
    <section
      className="card overflow-hidden"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        onFiles(e.dataTransfer.files, kind, topic);
      }}
      style={dragging ? { borderColor: "var(--brand-blue)", boxShadow: "0 0 0 2px var(--focus-ring)" } : undefined}
    >
      <header
        className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4"
        style={{ borderColor: "var(--glass-border)" }}
      >
        <div>
          <h2 className="text-lg font-semibold">{name}</h2>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {owner ? `Owner: ${owner} · ` : ""}
            {docs.length} document{docs.length === 1 ? "" : "s"} on file
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs" style={{ color: "var(--text-muted)" }}>
            Adding
            <select
              className="ml-1.5 rounded-lg border px-2 py-1.5 text-sm"
              style={{ borderColor: "var(--glass-border)", color: "var(--text)" }}
              value={kind}
              onChange={(e) => setKind(e.target.value as DocKind)}
            >
              {(Object.keys(KIND_LABELS) as DocKind[]).map((k) => (
                <option key={k} value={k}>
                  {KIND_LABELS[k]}
                </option>
              ))}
            </select>
          </label>
          {kind !== "report" && (
            <label className="text-xs" style={{ color: "var(--text-muted)" }}>
              Topic
              <select
                className="ml-1.5 rounded-lg border px-2 py-1.5 text-sm"
                style={{ borderColor: "var(--glass-border)", color: "var(--text)" }}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
              >
                {TOPICS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button type="button" onClick={() => inputRef.current?.click()} className="btn-primary px-4 py-2 text-sm">
            Add {kind === "report" ? "reports" : kind === "sop" ? "SOPs" : "deviation reports"}
          </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            onFiles(e.target.files, kind, topic);
            e.target.value = "";
          }}
        />
      </header>

      <div className="grid gap-6 p-5 md:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            Required records ({required.length})
          </p>
          <ul className="mt-2 flex flex-col gap-1.5 text-sm">
            {required.map((item) => (
              <li key={item.id}>
                <span className="font-medium">{item.item_name}</span>{" "}
                <span className="text-xs" style={{ color: "var(--brand-blue-text)" }}>
                  {item.citation}
                </span>
              </li>
            ))}
            {required.length === 0 && <li style={{ color: "var(--text-muted)" }}>No checklist items for this department.</li>}
          </ul>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
            On file
          </p>
          <ul className="mt-2 flex flex-col gap-2 text-sm">
            {pending.map((u) => (
              <li key={u.key} className="flex items-start gap-2">
                <StatusIcon tone={u.state === "failed" ? "bad" : "warn"} size={18} className="mt-0.5" />
                <span className="min-w-0">
                  <span className="block [overflow-wrap:anywhere]">{displayTitle(u.name)}</span>
                  <span className="text-xs" style={{ color: u.state === "failed" ? "var(--severity-critical)" : "var(--text-muted)" }}>
                    {u.state === "uploading" ? "Uploading..." : u.state === "processing" ? "Reading document..." : u.error}
                  </span>
                </span>
              </li>
            ))}
            {docs.map((doc) => (
              <li key={doc.id} className="flex items-start gap-2">
                <StatusIcon tone={doc.status === "processed" ? "good" : "bad"} size={18} className="mt-0.5" />
                <span className="min-w-0">
                  <span className="block [overflow-wrap:anywhere]">
                    {displayTitle(doc.title)}
                    {doc.type !== "report" && (
                      <span
                        className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                        style={{ background: "var(--tint-violet)", color: "#6d28d9" }}
                      >
                        {doc.type === "sop" ? "SOP" : "Deviation"} · content checked
                      </span>
                    )}
                  </span>
                  {doc.status !== "processed" && (
                    <span className="text-xs" style={{ color: "var(--severity-critical)" }}>
                      {doc.processing_error ?? `Not processed (${doc.status})`}
                    </span>
                  )}
                </span>
              </li>
            ))}
            {docs.length === 0 && pending.length === 0 && (
              <li
                className="rounded-lg border-2 border-dashed px-4 py-6 text-center text-sm"
                style={{ borderColor: "var(--glass-border)", color: "var(--text-muted)" }}
              >
                No documents yet. Choose what you're adding, then click <strong>Add</strong> or drop files here.
              </li>
            )}
          </ul>
        </div>
      </div>
    </section>
  );
}
