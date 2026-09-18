import { GlassPanel } from "../components/GlassPanel";

export function Upload() {
  return (
    <GlassPanel className="mx-auto max-w-2xl text-center">
      <h1 className="text-2xl font-semibold">Upload documents</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Drag and drop SOPs, deviation reports, or batch/device records. Document
        type is detected automatically as files are added.
      </p>
      <div
        className="mt-6 flex h-40 items-center justify-center rounded-2xl border-2 border-dashed"
        style={{ borderColor: "var(--glass-border)" }}
      >
        <span style={{ color: "var(--text-muted)" }}>Drop files here (Milestone 4)</span>
      </div>
    </GlassPanel>
  );
}
