import { GlassPanel, SeverityChip } from "../components/GlassPanel";

const PLACEHOLDER_FINDINGS = [
  {
    id: "placeholder-1",
    clause: "QMSR 820.100(a)(2)",
    document: "Deviation Report — DEV-0142",
    severity: "critical" as const,
    excerpt: "Investigation section does not document a root-cause analysis.",
  },
  {
    id: "placeholder-2",
    clause: "ISO 13485 §8.5.2",
    document: "SOP-QA-014 Deviation Handling",
    severity: "major" as const,
    excerpt: "SOP does not specify effectiveness review timing for corrective action.",
  },
];

export function Dashboard() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">Findings</h1>
      <p style={{ color: "var(--text-muted)" }}>
        Backed by <code>GET /findings</code> — empty until Milestone 3 populates real findings.
        Shown below are layout placeholders.
      </p>
      {PLACEHOLDER_FINDINGS.map((finding) => (
        <GlassPanel key={finding.id} className="flex items-start justify-between gap-4">
          <div>
            <div className="font-medium">{finding.document}</div>
            <div className="text-sm" style={{ color: "var(--text-muted)" }}>
              {finding.clause}
            </div>
            <p className="mt-2 text-sm">{finding.excerpt}</p>
          </div>
          <SeverityChip severity={finding.severity} />
        </GlassPanel>
      ))}
    </div>
  );
}
