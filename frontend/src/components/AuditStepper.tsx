const STEPS = ["Audit details", "Documents", "Results"];

/** Progress indicator for the new-simulation flow: details -> documents -> results. */
export function AuditStepper({ current, runCode }: { current: 0 | 1 | 2; runCode?: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      {runCode && (
        <span
          className="mr-1 rounded-full px-2.5 py-1 text-xs font-semibold"
          style={{ background: "var(--tint-blue)", color: "var(--brand-blue-text)" }}
        >
          {runCode}
        </span>
      )}
      {STEPS.map((label, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <div key={label} className="flex items-center gap-3">
            <span className="flex items-center gap-2">
              <span
                className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold"
                style={
                  active || done
                    ? { backgroundImage: "var(--brand-gradient)", color: "#fff" }
                    : { background: "#f1f5f9", color: "var(--text-muted)" }
                }
              >
                {done ? "✓" : index + 1}
              </span>
              <span
                className="text-sm font-medium"
                style={{ color: active ? "var(--text)" : "var(--text-muted)" }}
              >
                {label}
              </span>
            </span>
            {index < STEPS.length - 1 && <span aria-hidden className="h-px w-8" style={{ background: "#cbd5e1" }} />}
          </div>
        );
      })}
    </div>
  );
}
