import { useState } from "react";
import { useNavigate } from "react-router-dom";
import loginBackground from "../assets/login-background.png";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

// This page has its own fixed dark visual identity (background image +
// scrim) independent of the viewer's OS light/dark preference, so its
// surface colors are hardcoded rather than pulled from the theme-aware
// --surface-bg/--surface-text tokens used everywhere else in the app.
const INPUT_STYLE = {
  backgroundColor: "#1e293b",
  color: "#f1f5f9",
  borderColor: "rgba(255,255,255,0.25)",
};

export function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [orgName, setOrgName] = useState("");
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
        await register(orgName, industry, email, password);
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4 py-12"
      style={{
        backgroundImage: `linear-gradient(180deg, rgba(4,12,26,0.55), rgba(4,12,26,0.82)), url(${loginBackground})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundColor: "#06111f",
      }}
    >
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-white">DeviationTrace</h1>
          <p className="mt-2 text-base text-slate-300">Audit-readiness gap detection</p>
        </div>

        <div
          className="rounded-2xl border p-8 shadow-2xl"
          style={{ backgroundColor: "rgba(15, 23, 42, 0.72)", borderColor: "rgba(255,255,255,0.15)" }}
        >
          <div className="mb-6 flex gap-6 text-base text-slate-200">
            <button
              type="button"
              className={mode === "login" ? "font-semibold text-white underline" : ""}
              onClick={() => setMode("login")}
            >
              Log in
            </button>
            <button
              type="button"
              className={mode === "register" ? "font-semibold text-white underline" : ""}
              onClick={() => setMode("register")}
            >
              Register organization
            </button>
          </div>

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            {mode === "register" && (
              <>
                <label className="text-base text-slate-200">
                  Organization name
                  <input
                    className="mt-1.5 w-full rounded-lg border px-4 py-2.5 text-base"
                    style={INPUT_STYLE}
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    required
                  />
                </label>
                <label className="text-base text-slate-200">
                  Industry
                  <select
                    className="mt-1.5 w-full rounded-lg border px-4 py-2.5 text-base"
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

            <label className="text-base text-slate-200">
              Email
              <input
                type="email"
                className="mt-1.5 w-full rounded-lg border px-4 py-2.5 text-base"
                style={INPUT_STYLE}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>

            <label className="text-base text-slate-200">
              Password
              <input
                type="password"
                className="mt-1.5 w-full rounded-lg border px-4 py-2.5 text-base"
                style={INPUT_STYLE}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </label>

            {error && <p className="text-base text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 rounded-lg border px-4 py-3 text-base font-semibold text-white transition-colors hover:bg-white/10"
              style={{ borderColor: "rgba(255,255,255,0.3)" }}
            >
              {submitting ? "Please wait..." : mode === "login" ? "Log in" : "Create organization"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
