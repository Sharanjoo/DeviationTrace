/** The single blurred layer behind every glass panel. Blurring once here
 * (instead of giving each GlassPanel its own backdrop-filter) avoids the
 * performance cost of stacking many blurred layers, per the PRD's UI note. */
export function Background() {
  return (
    <div
      aria-hidden
      className="fixed inset-0 -z-10"
      style={{
        background: "linear-gradient(160deg, var(--gradient-start), var(--gradient-end))",
        filter: `blur(${"var(--glass-blur)"})`,
        transform: "scale(1.1)",
      }}
    />
  );
}
