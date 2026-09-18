import { GlassPanel } from "../components/GlassPanel";

const STEPS = ["Classify", "Extract", "Cross-check"];

export function Processing() {
  return (
    <GlassPanel className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold">Processing</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Pipeline progress polls <code>GET /documents/&#123;id&#125;/status</code>.
      </p>
      <ol className="mt-6 space-y-3">
        {STEPS.map((step) => (
          <li
            key={step}
            className="rounded-xl border px-4 py-3"
            style={{ borderColor: "var(--glass-border)" }}
          >
            {step}
          </li>
        ))}
      </ol>
    </GlassPanel>
  );
}
