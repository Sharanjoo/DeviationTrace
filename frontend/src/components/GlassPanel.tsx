import type { PropsWithChildren } from "react";
import { TRIAGE_LABELS, type TriageDecisionValue } from "../triage";

/** White card with a hairline border and soft shadow, sitting on the page
 * wash. Name kept from the earlier glass theme so every page restyles. */
export function GlassPanel({
  children,
  className = "",
}: PropsWithChildren<{ className?: string }>) {
  return (
    <div
      className={`border p-6 ${className}`}
      style={{
        background: "var(--glass-panel-bg)",
        borderColor: "var(--glass-border)",
        borderRadius: "var(--glass-radius)",
        boxShadow: "var(--glass-shadow)",
      }}
    >
      {children}
    </div>
  );
}

const SEVERITY_LABELS = {
  critical: "Critical",
  major: "Major",
  minor: "Minor",
  resolved: "Resolved",
} as const;

export function SeverityChip({ severity }: { severity: keyof typeof SEVERITY_LABELS }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{ background: `var(--severity-${severity}-tint)`, color: `var(--severity-${severity})` }}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: `var(--severity-${severity})` }} />
      {SEVERITY_LABELS[severity]}
    </span>
  );
}

/** Outlined (not filled) so it never reads as a second severity signal. */
export function TriageChip({ decision }: { decision: TriageDecisionValue | null | undefined }) {
  return (
    <span
      className="rounded-full border px-3 py-1 text-xs font-medium"
      style={{
        borderColor: "var(--glass-border)",
        color: decision ? "var(--text)" : "var(--text-muted)",
      }}
    >
      {decision ? TRIAGE_LABELS[decision] : "Pending"}
    </span>
  );
}
