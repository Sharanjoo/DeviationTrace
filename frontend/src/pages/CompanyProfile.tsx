import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useOnboarding } from "../context/OnboardingContext";
import { displayName, initials, ROLE_LABELS, ROLES, type Member, type OrgProfile } from "../orgProfile";

const INDUSTRY_LABELS: Record<string, string> = { device: "Medical device", drug: "Drug manufacturer" };
const INPUT = "mt-1.5 w-full rounded-lg border px-3 py-2 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)", color: "var(--text)" };
const muted = { color: "var(--text-muted)" };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

const ROLE_STYLE: Record<string, { background: string; color: string }> = {
  admin: { background: "var(--tint-violet)", color: "#6d28d9" },
  member: { background: "var(--tint-blue)", color: "var(--brand-blue-text)" },
  viewer: { background: "#f1f5f9", color: "#475569" },
};

/** The company's details and who has access. Admins (the people in charge)
 * add and remove members and change their roles. */
export function CompanyProfile() {
  const { refresh: refreshOnboarding } = useOnboarding();
  const [profile, setProfile] = useState<OrgProfile | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(
    () =>
      Promise.all([api.get<OrgProfile>("/org/profile"), api.get<Member[]>("/org/members")])
        .then(([p, m]) => {
          setProfile(p);
          setMembers(m);
        })
        .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load the company profile.")),
    [],
  );

  useEffect(() => {
    load();
  }, [load]);

  if (!profile) {
    return error ? (
      <p className="text-center" style={{ color: "var(--severity-critical)" }}>
        {error}
      </p>
    ) : (
      <p className="text-center" style={muted}>
        Loading company profile...
      </p>
    );
  }

  const isAdmin = profile.you.role === "admin";

  const changeRole = async (member: Member, role: string) => {
    setBusyId(member.id);
    setError(null);
    try {
      await api.patch(`/org/members/${member.id}`, { role });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't change the role.");
    } finally {
      setBusyId(null);
    }
  };

  const removeMember = async (member: Member) => {
    if (!window.confirm(`Remove ${displayName(member)}? They'll lose access to ${profile.name} straight away.`)) return;
    setBusyId(member.id);
    setError(null);
    try {
      await api.del(`/org/members/${member.id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove the member.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <p className="eyebrow">Company profile</p>
        <h1 className="mt-2 text-3xl font-bold">{profile.name}</h1>
        <p className="mt-2" style={muted}>
          Your company's details and the people who can access DeviationTrace.{" "}
          {isAdmin
            ? "As an admin, you can add members and change what they can do."
            : "Only admins can add or change members."}
        </p>
      </div>

      <CompanyDetails
        profile={profile}
        isAdmin={isAdmin}
        onSaved={async () => {
          await load();
          await refreshOnboarding();
        }}
      />

      <section className="card overflow-hidden">
        <header
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4"
          style={{ borderColor: "var(--glass-border)" }}
        >
          <div>
            <h2 className="text-lg font-semibold">Members ({members.length})</h2>
            <p className="text-sm" style={muted}>
              Everyone who can sign in to {profile.name}.
            </p>
          </div>
        </header>

        {error && (
          <p className="px-5 pt-4 text-sm" style={{ color: "var(--severity-critical)" }}>
            {error}
          </p>
        )}

        <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
          {members.map((m) => {
            const isYou = m.id === profile.you.id;
            return (
              <li
                key={m.id}
                className="flex flex-wrap items-center gap-4 px-5 py-4"
                style={{ borderColor: "var(--glass-border)" }}
              >
                <span
                  aria-hidden
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
                  style={{ backgroundImage: "var(--brand-gradient)" }}
                >
                  {initials(displayName(m))}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">
                    {displayName(m)}
                    {isYou && (
                      <span className="ml-2 text-xs font-normal" style={muted}>
                        (you)
                      </span>
                    )}
                  </p>
                  <p className="truncate text-sm" style={muted}>
                    {m.email} · added {formatDate(m.created_at)}
                  </p>
                </div>
                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <select
                      aria-label={`Role for ${displayName(m)}`}
                      className="rounded-lg border px-3 py-2 text-sm"
                      style={INPUT_STYLE}
                      value={m.role}
                      disabled={busyId === m.id}
                      onChange={(e) => changeRole(m, e.target.value)}
                    >
                      {ROLES.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      ))}
                    </select>
                    {!isYou && (
                      <button
                        type="button"
                        onClick={() => removeMember(m)}
                        disabled={busyId === m.id}
                        className="btn-secondary px-3 py-2 text-xs"
                        style={{ color: "var(--severity-critical)" }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="rounded-full px-2.5 py-1 text-xs font-semibold" style={ROLE_STYLE[m.role]}>
                    {ROLE_LABELS[m.role] ?? m.role}
                  </span>
                )}
              </li>
            );
          })}
        </ul>

        {isAdmin && <AddMember onAdded={load} />}
      </section>

      <section className="card p-5">
        <h2 className="font-semibold">What each role can do</h2>
        <dl className="mt-3 grid gap-4 sm:grid-cols-3">
          {ROLES.map((r) => (
            <div key={r.value}>
              <dt>
                <span className="rounded-full px-2.5 py-1 text-xs font-semibold" style={ROLE_STYLE[r.value]}>
                  {r.label}
                </span>
              </dt>
              <dd className="mt-2 text-sm" style={muted}>
                {r.description}
              </dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

function CompanyDetails({
  profile,
  isAdmin,
  onSaved,
}: {
  profile: OrgProfile;
  isAdmin: boolean;
  onSaved: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(profile.name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.patch("/org/profile", { name });
      await onSaved();
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const fields = [
    { label: "Industry", value: INDUSTRY_LABELS[profile.industry] ?? profile.industry },
    { label: "Audit scope", value: profile.scope_label ?? "Standard checklist" },
    { label: "Set up", value: profile.onboarded_at ? formatDate(profile.onboarded_at) : "Not finished" },
    { label: "Your role", value: ROLE_LABELS[profile.you.role] ?? profile.you.role },
  ];

  return (
    <section className="card p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-lg font-semibold">Company details</h2>
        {isAdmin && !editing && (
          <button type="button" onClick={() => setEditing(true)} className="btn-secondary px-3 py-1.5 text-xs">
            Edit name
          </button>
        )}
      </div>
      {editing && (
        <form onSubmit={save} className="mt-3 flex flex-wrap items-end gap-2">
          <label className="min-w-[240px] flex-1 text-sm font-medium">
            Company name
            <input
              className={INPUT}
              style={INPUT_STYLE}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={255}
            />
          </label>
          <button type="submit" disabled={saving} className="btn-primary px-4 py-2 text-sm">
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            type="button"
            onClick={() => {
              setEditing(false);
              setName(profile.name);
            }}
            className="btn-secondary px-4 py-2 text-sm"
          >
            Cancel
          </button>
        </form>
      )}
      {error && (
        <p className="mt-2 text-sm" style={{ color: "var(--severity-critical)" }}>
          {error}
        </p>
      )}
      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
        {fields.map((f) => (
          <div key={f.label}>
            <dt className="text-xs" style={muted}>
              {f.label}
            </dt>
            <dd className="mt-0.5 font-semibold">{f.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function AddMember({ onAdded }: { onAdded: () => Promise<unknown> }) {
  const [open, setOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ name: string; email: string; password: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const result = await api.post<{ member: Member; temporary_password: string }>("/org/members", {
        full_name: fullName,
        email,
        role,
      });
      setCreated({ name: displayName(result.member), email: result.member.email, password: result.temporary_password });
      setFullName("");
      setEmail("");
      setRole("member");
      setOpen(false);
      await onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add the member.");
    } finally {
      setSaving(false);
    }
  };

  const copy = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.password);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="border-t p-5" style={{ borderColor: "var(--glass-border)" }}>
      {created && (
        <div
          className="mb-4 rounded-xl border p-4"
          style={{ borderColor: "var(--brand-blue)", background: "var(--tint-blue)" }}
        >
          <p className="font-semibold">{created.name} can now sign in.</p>
          <p className="mt-1 text-sm" style={muted}>
            Give them their email ({created.email}) and this temporary password. It's shown only once.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <code
              className="rounded-lg border bg-white px-3 py-2 text-sm"
              style={{ borderColor: "var(--glass-border)" }}
            >
              {created.password}
            </code>
            <button type="button" onClick={copy} className="btn-secondary px-3 py-2 text-xs">
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              type="button"
              onClick={() => {
                setCreated(null);
                setCopied(false);
              }}
              className="text-xs underline"
              style={muted}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {!open ? (
        <button type="button" onClick={() => setOpen(true)} className="btn-primary px-4 py-2 text-sm">
          Add member
        </button>
      ) : (
        <form onSubmit={submit}>
          <h3 className="font-semibold">Add a member</h3>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            <label className="text-sm font-medium">
              Full name
              <input
                className={INPUT}
                style={INPUT_STYLE}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                autoComplete="off"
              />
            </label>
            <label className="text-sm font-medium">
              Work email
              <input
                type="email"
                className={INPUT}
                style={INPUT_STYLE}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="off"
              />
            </label>
            <label className="text-sm font-medium">
              Role
              <select className={INPUT} style={INPUT_STYLE} value={role} onChange={(e) => setRole(e.target.value)}>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="mt-2 text-xs" style={muted}>
            {ROLES.find((r) => r.value === role)?.description}
          </p>
          {error && (
            <p className="mt-2 text-sm" style={{ color: "var(--severity-critical)" }}>
              {error}
            </p>
          )}
          <div className="mt-4 flex gap-2">
            <button type="submit" disabled={saving} className="btn-primary px-4 py-2 text-sm">
              {saving ? "Adding..." : "Add member"}
            </button>
            <button type="button" onClick={() => setOpen(false)} className="btn-secondary px-4 py-2 text-sm">
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
