import type { PropsWithChildren, ReactNode } from "react";
import { Link } from "react-router-dom";

/** Shared building blocks for the verification-check result pages
 * (Internal Audit Simulation, Vendor Audit Cross-Check). Each check keeps
 * its own data and statuses; these only render them consistently. */

export type Tone = "bad" | "warn" | "good";

const TONE_COLOR: Record<Tone, string> = {
  bad: "var(--severity-critical)",
  warn: "var(--severity-major)",
  good: "var(--severity-resolved)",
};
const TONE_TINT: Record<Tone, string> = {
  bad: "var(--severity-critical-tint)",
  warn: "var(--severity-major-tint)",
  good: "var(--severity-resolved-tint)",
};

export interface StatusDef {
  value: string;
  label: string;
  tone: Tone;
}

// ---------------------------------------------------------------- header

export function CheckHeader({
  eyebrow,
  title,
  description,
  meta,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  meta?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-bold">{title}</h1>
        <p className="mt-2" style={{ color: "var(--text-muted)" }}>
          {description}
        </p>
        {meta && (
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            {meta}
          </p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

// ------------------------------------------------------------ stat cards

/** Readiness % plus one card per status. Status cards act as a filter:
 * click to show only that status, click again to clear. */
export function StatCards({
  scoreLabel,
  statuses,
  counts,
  active,
  onSelect,
}: {
  scoreLabel: string;
  statuses: StatusDef[];
  counts: Record<string, number>;
  active: string;
  onSelect: (status: string) => void;
}) {
  const total = statuses.reduce((sum, s) => sum + (counts[s.value] ?? 0), 0);
  const good = statuses.filter((s) => s.tone === "good").reduce((sum, s) => sum + (counts[s.value] ?? 0), 0);
  const readiness = total ? Math.round((good / total) * 100) : 0;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div className="card col-span-2 p-5 md:col-span-1">
        <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          {scoreLabel}
        </p>
        <p className="mt-1 text-3xl font-bold text-gradient">{total ? `${readiness}%` : "—"}</p>
        <ProgressBar counts={counts} statuses={statuses} className="mt-3" />
        <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          {good} of {total} requirements met
        </p>
      </div>
      {statuses.map((s) => {
        const isActive = active === s.value;
        return (
          <button
            key={s.value}
            type="button"
            aria-pressed={isActive}
            onClick={() => onSelect(isActive ? "" : s.value)}
            className="card p-5 text-left transition-shadow hover:shadow-md"
            style={isActive ? { borderColor: TONE_COLOR[s.tone], boxShadow: `0 0 0 1px ${TONE_COLOR[s.tone]}` } : undefined}
          >
            <span className="flex items-center gap-2 text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              <StatusIcon tone={s.tone} size={18} />
              {s.label}
            </span>
            <p className="mt-1 text-3xl font-bold" style={{ color: TONE_COLOR[s.tone] }}>
              {counts[s.value] ?? 0}
            </p>
            <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
              {isActive ? "Showing only these · click to clear" : "Click to filter"}
            </p>
          </button>
        );
      })}
    </div>
  );
}

/** Stacked bar: one segment per status, in status order. */
export function ProgressBar({
  statuses,
  counts,
  className = "",
}: {
  statuses: StatusDef[];
  counts: Record<string, number>;
  className?: string;
}) {
  const total = statuses.reduce((sum, s) => sum + (counts[s.value] ?? 0), 0);
  // Met requirements first, so the bar reads as "how far along".
  const ordered = [...statuses].sort((a, b) => (a.tone === "good" ? -1 : b.tone === "good" ? 1 : 0));
  return (
    <div className={`flex h-2 w-full overflow-hidden rounded-full ${className}`} style={{ background: "#f1f5f9" }}>
      {total > 0 &&
        ordered.map((s) => {
          const n = counts[s.value] ?? 0;
          return n ? (
            <div
              key={s.value}
              title={`${n} ${s.label.toLowerCase()}`}
              style={{ width: `${(n / total) * 100}%`, background: TONE_COLOR[s.tone] }}
            />
          ) : null;
        })}
    </div>
  );
}

// ------------------------------------------------------------ filter chips

export function FilterChips({
  options,
  value,
  onChange,
  allLabel,
}: {
  options: { value: string; label: string; count?: number }[];
  value: string;
  onChange: (value: string) => void;
  allLabel: string;
}) {
  const chip = (v: string, label: string, count?: number) => {
    const active = value === v;
    return (
      <button
        key={v || "all"}
        type="button"
        aria-pressed={active}
        onClick={() => onChange(v)}
        className="shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors"
        style={
          active
            ? { background: "var(--tint-blue)", borderColor: "var(--brand-blue)", color: "var(--brand-blue-text)" }
            : { background: "#fff", borderColor: "var(--glass-border)", color: "#4b5563" }
        }
      >
        {label}
        {count !== undefined && <span className="ml-1.5 opacity-60">{count}</span>}
      </button>
    );
  };
  return (
    <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
      {chip("", allLabel)}
      {options.map((o) => chip(o.value, o.label, o.count))}
    </div>
  );
}

// ------------------------------------------------------------ result groups

export function GroupCard({
  title,
  subtitle,
  badge,
  statuses,
  counts,
  action,
  children,
}: PropsWithChildren<{
  title: string;
  subtitle?: ReactNode;
  badge?: ReactNode;
  statuses: StatusDef[];
  counts: Record<string, number>;
  action?: ReactNode;
}>) {
  const total = statuses.reduce((sum, s) => sum + (counts[s.value] ?? 0), 0);
  return (
    <section className="card overflow-hidden">
      <header className="flex flex-col gap-3 border-b p-5 sm:flex-row sm:items-center sm:justify-between" style={{ borderColor: "var(--glass-border)" }}>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold [overflow-wrap:anywhere]">{title}</h2>
            {badge}
          </div>
          {subtitle && (
            <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
              {subtitle}
            </p>
          )}
          {total > 0 && (
            <div className="mt-3 flex items-center gap-3">
              <ProgressBar statuses={statuses} counts={counts} className="max-w-xs" />
              <span className="shrink-0 text-xs" style={{ color: "var(--text-muted)" }}>
                {statuses
                  .filter((s) => counts[s.value])
                  .map((s) => `${counts[s.value]} ${s.label.toLowerCase()}`)
                  .join(" · ")}
              </span>
            </div>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
        {children}
      </ul>
    </section>
  );
}

export function ResultRow({
  status,
  title,
  citation,
  explanation,
  footnote,
}: {
  status: StatusDef;
  title: string;
  citation: string;
  explanation: string;
  footnote?: ReactNode;
}) {
  return (
    <li className="flex gap-4 px-5 py-4" style={{ borderColor: "var(--glass-border)" }}>
      <StatusIcon tone={status.tone} size={22} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <p className="font-semibold">{title}</p>
          <StatusPill status={status} />
        </div>
        <p className="mt-0.5 text-xs font-medium" style={{ color: "var(--brand-blue-text)" }}>
          {citation}
        </p>
        <p className="mt-1.5 text-sm" style={{ color: "var(--text-muted)" }}>
          {explanation}
        </p>
        {footnote && <p className="mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>{footnote}</p>}
      </div>
    </li>
  );
}

export function StatusPill({ status }: { status: StatusDef }) {
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ background: TONE_TINT[status.tone], color: TONE_COLOR[status.tone] }}
    >
      {status.label}
    </span>
  );
}

export function StatusIcon({ tone, size = 20, className = "" }: { tone: Tone; size?: number; className?: string }) {
  const path =
    tone === "good" ? "M8 12.5l2.5 2.5L16 9.5" : tone === "warn" ? "M12 8v4.5M12 16h.01" : "M9 9l6 6M15 9l-6 6";
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 items-center justify-center rounded-full ${className}`}
      style={{ width: size, height: size, background: TONE_TINT[tone] }}
    >
      <svg width={size * 0.75} height={size * 0.75} viewBox="0 0 24 24" fill="none" stroke={TONE_COLOR[tone]} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d={path} />
      </svg>
    </span>
  );
}

// ------------------------------------------------------------ empty state

export function EmptyState({
  title,
  body,
  actionLabel,
  actionTo,
  onAction,
}: {
  title: string;
  body: string;
  actionLabel?: string;
  actionTo?: string;
  onAction?: () => void;
}) {
  return (
    <div className="card flex flex-col items-center px-6 py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl" style={{ background: "var(--tint-blue)" }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--brand-blue)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M12 18v-6M9 15h6" />
        </svg>
      </span>
      <p className="mt-4 text-lg font-semibold">{title}</p>
      <p className="mt-1 max-w-md text-sm" style={{ color: "var(--text-muted)" }}>
        {body}
      </p>
      {actionLabel && actionTo && (
        <Link to={actionTo} className="btn-primary mt-5 px-4 py-2 text-sm">
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionTo && (
        <button type="button" onClick={onAction} className="btn-primary mt-5 px-4 py-2 text-sm">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
