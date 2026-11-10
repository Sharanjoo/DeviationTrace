/** DeviationTrace wordmark: a gradient tile with a check-on-trace glyph. */
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden
        className="inline-flex items-center justify-center rounded-lg"
        style={{ width: size, height: size, backgroundImage: "var(--brand-gradient)" }}
      >
        <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" fill="none">
          <path d="M3 13h4l2-5 4 10 2-5h6" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      <span className="text-lg font-bold tracking-tight" style={{ color: "var(--text)" }}>
        Deviation<span className="text-gradient">Trace</span>
      </span>
    </span>
  );
}
