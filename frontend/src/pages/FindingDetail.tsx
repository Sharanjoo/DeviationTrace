import { GlassPanel, SeverityChip } from "../components/GlassPanel";

export function FindingDetail() {
  return (
    <GlassPanel className="mx-auto max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Finding detail</h1>
        <SeverityChip severity="major" />
      </div>
      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Clause text
      </h2>
      <p className="mt-1 text-sm">
        Placeholder — full clause text from <code>RegulatoryClause.requirement_text</code>{" "}
        renders here.
      </p>
      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Source passage
      </h2>
      <p className="mt-1 text-sm">
        Placeholder — highlighted excerpt from <code>DocumentSection.text</code>.
      </p>
      <h2 className="mt-4 text-sm font-medium" style={{ color: "var(--text-muted)" }}>
        Triage
      </h2>
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          className="rounded-lg border px-3 py-1.5 text-sm"
          style={{ borderColor: "var(--glass-border)" }}
        >
          Confirmed
        </button>
        <button
          type="button"
          className="rounded-lg border px-3 py-1.5 text-sm"
          style={{ borderColor: "var(--glass-border)" }}
        >
          False positive
        </button>
        <button
          type="button"
          className="rounded-lg border px-3 py-1.5 text-sm"
          style={{ borderColor: "var(--glass-border)" }}
        >
          Needs SME
        </button>
      </div>
    </GlassPanel>
  );
}
