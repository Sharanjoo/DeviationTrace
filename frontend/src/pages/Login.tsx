import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { Background } from "../components/Background";
import { Logo } from "../components/Logo";
import { useAuth } from "../context/AuthContext";

const INPUT_CLASS = "mt-1.5 w-full rounded-lg border px-4 py-2.5 text-base";
const INPUT_STYLE = { borderColor: "var(--glass-border)" };

const FEATURES = [
  {
    title: "Internal audit simulation",
    body: "Check every department's required records exist and are complete before the auditor asks.",
    tint: "var(--tint-blue)",
    color: "var(--brand-blue)",
    icon: "M9 11l3 3L22 4M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11",
  },
  {
    title: "Vendor audit cross-check",
    body: "Verify supplier audit reports against your vendor standards, claim by claim.",
    tint: "var(--tint-violet)",
    color: "var(--brand-violet)",
    icon: "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75",
  },
  {
    title: "Evidence-linked findings",
    body: "Every gap cites QMSR, ISO 13485 or 21 CFR 211 and the passage it came from.",
    tint: "var(--tint-blue)",
    color: "var(--brand-blue)",
    icon: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
  },
];

export function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [orgName, setOrgName] = useState("");
  const [fullName, setFullName] = useState("");
  const [industry, setIndustry] = useState("device");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(orgName, industry, email, password, fullName);
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  const tabClass = (active: boolean) =>
    `flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${active ? "bg-white shadow-sm" : ""}`;

  return (
    <div className="min-h-screen">
      <Background />
      <header className="mx-auto max-w-6xl px-4 py-5">
        <Logo />
      </header>

      <main className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-10 lg:grid-cols-2 lg:py-16">
        <section>
          <p className="eyebrow">Audit-readiness validation</p>
          <h1 className="mt-4 text-4xl font-bold sm:text-5xl">
            No surprises
            <br />
            <span className="text-gradient">at audit.</span>
          </h1>
          <p className="mt-5 max-w-lg text-lg leading-relaxed" style={{ color: "var(--text-muted)" }}>
            DeviationTrace cross-checks your SOPs, records, deviations and vendor audits against FDA and ISO
            requirements, so gaps surface on your schedule, not the inspector's.
          </p>

          <ul className="mt-8 flex flex-col gap-3">
            {FEATURES.map((f) => (
              <li
                key={f.title}
                className="flex items-start gap-4 rounded-2xl border bg-white p-4"
                style={{ borderColor: "var(--glass-border)", boxShadow: "var(--glass-shadow)" }}
              >
                <span
                  aria-hidden
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                  style={{ background: f.tint }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={f.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d={f.icon} />
                  </svg>
                </span>
                <div>
                  <p className="font-semibold">{f.title}</p>
                  <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
                    {f.body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section
          className="order-first w-full justify-self-center rounded-2xl border bg-white p-8 lg:order-none lg:justify-self-end"
          style={{ borderColor: "var(--glass-border)", boxShadow: "0 20px 50px rgba(15,23,42,0.10)", maxWidth: 440 }}
        >
          <h2 className="text-2xl font-bold">{mode === "login" ? "Welcome back" : "Create your organization"}</h2>
          <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
            {mode === "login" ? "Log in to continue to your workspace." : "Set up a workspace for your quality team."}
          </p>

          <div className="mt-6 flex gap-1 rounded-lg p-1" style={{ background: "#f3f4f6" }}>
            <button type="button" className={tabClass(mode === "login")} onClick={() => setMode("login")}>
              Log in
            </button>
            <button type="button" className={tabClass(mode === "register")} onClick={() => setMode("register")}>
              Register organization
            </button>
          </div>

          <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
            {mode === "register" && (
              <>
                <label className="text-sm font-medium">
                  Organization name
                  <input
                    className={INPUT_CLASS}
                    style={INPUT_STYLE}
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    required
                  />
                </label>
                <label className="text-sm font-medium">
                  Your name
                  <input
                    className={INPUT_CLASS}
                    style={INPUT_STYLE}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    autoComplete="name"
                    required
                  />
                </label>
                <label className="text-sm font-medium">
                  Industry
                  <select
                    className={INPUT_CLASS}
                    style={INPUT_STYLE}
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                  >
                    <option value="device">Medical device</option>
                    <option value="drug">Drug manufacturer</option>
                  </select>
                </label>
              </>
            )}

            <label className="text-sm font-medium">
              Email
              <input
                type="email"
                className={INPUT_CLASS}
                style={INPUT_STYLE}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>

            <label className="text-sm font-medium">
              Password
              <input
                type="password"
                className={INPUT_CLASS}
                style={INPUT_STYLE}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </label>

            {error && (
              <p className="text-sm" style={{ color: "var(--severity-critical)" }}>
                {error}
              </p>
            )}

            <button type="submit" disabled={submitting} className="btn-primary mt-2 px-4 py-3 text-base">
              {submitting ? "Please wait..." : mode === "login" ? "Log in" : "Create organization"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
