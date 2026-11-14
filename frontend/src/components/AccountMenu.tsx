import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useOnboarding } from "../context/OnboardingContext";
import { displayName, ROLE_LABELS, type OrgProfile } from "../orgProfile";

const INDUSTRY_LABELS: Record<string, string> = { device: "Medical device", drug: "Drug manufacturer" };

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] ?? "?").slice(0, 2)).toUpperCase();
}

/** Header account control: who you're signed in as, with Log out tucked
 * inside so it isn't sitting next to everyday actions. */
export function AccountMenu() {
  const { logout, token } = useAuth();
  const { status } = useOnboarding();
  const [open, setOpen] = useState(false);
  // Who's signed in, shown in the menu. Re-read when the menu opens, so a
  // name or role change made elsewhere shows up.
  const [profile, setProfile] = useState<OrgProfile | null>(null);
  useEffect(() => {
    if (!token) return;
    api.get<OrgProfile>("/org/profile").then(setProfile).catch(() => setProfile(null));
  }, [token, open]);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const orgName = profile?.name ?? status?.org_name ?? "Your organization";
  const details = status
    ? [INDUSTRY_LABELS[status.industry] ?? status.industry, status.completed ? status.scope_label ?? "Standard checklist" : null]
        .filter(Boolean)
        .join(" · ")
    : "";

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={`Account menu for ${orgName}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2.5 rounded-full border py-1 pr-3 pl-1 text-sm font-medium transition-colors hover:bg-slate-50"
        style={{ borderColor: "var(--glass-border)", background: "#fff" }}
      >
        <span
          aria-hidden
          className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white"
          style={{ backgroundImage: "var(--brand-gradient)" }}
        >
          {initials(orgName)}
        </span>
        <span className="hidden max-w-[180px] truncate sm:inline">{orgName}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d={open ? "M18 15l-6-6-6 6" : "M6 9l6 6 6-6"} />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="card absolute right-0 z-30 mt-2 w-64 overflow-hidden p-1.5"
          style={{ boxShadow: "0 12px 32px rgba(15,23,42,0.14)" }}
        >
          <div className="px-3 py-2.5">
            <p className="font-semibold">{orgName}</p>
            {details && (
              <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                {details}
              </p>
            )}
            {profile && (
              <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
                Signed in as <strong style={{ color: "var(--text)" }}>{displayName(profile.you)}</strong> ·{" "}
                {ROLE_LABELS[profile.you.role] ?? profile.you.role}
              </p>
            )}
          </div>
          <div className="my-1 border-t" style={{ borderColor: "var(--glass-border)" }} />
          {status?.completed && (
            <Link
              to="/company"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100"
            >
              Company profile &amp; members
            </Link>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={logout}
            className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100"
            style={{ color: "var(--severity-critical)" }}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
