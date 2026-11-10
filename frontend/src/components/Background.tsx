/** Fixed page wash behind every card: a soft blue-to-white-to-lavender
 * diagonal gradient. No blur needed now that cards are opaque white. */
export function Background() {
  return (
    <div
      aria-hidden
      className="fixed inset-0 -z-10"
      style={{
        background:
          "linear-gradient(135deg, var(--gradient-start) 0%, var(--gradient-mid) 50%, var(--gradient-end) 100%)",
      }}
    />
  );
}
