import type { PropsWithChildren } from "react";
import { TRIAGE_LABELS, type TriageDecisionValue } from "../triage";

/** Solid-translucent card sitting on top of the blurred Background — no
 * backdrop-filter of its own, per the PRD's stacking-blur performance note. */
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
      className="rounded-full px-3 py-1 text-xs font-medium text-slate-900"
      style={{ background: `var(--severity-${severity})` }}
    >
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
