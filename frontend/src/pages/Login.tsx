import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GlassPanel } from "../components/GlassPanel";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

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
    <GlassPanel className="mx-auto max-w-md">
      <div className="mb-4 flex gap-4 text-sm">
        <button
          type="button"
          className={mode === "login" ? "font-semibold underline" : ""}
          onClick={() => setMode("login")}
        >
          Log in
        </button>
        <button
          type="button"
          className={mode === "register" ? "font-semibold underline" : ""}
          onClick={() => setMode("register")}
        >
          Register organization
        </button>
      </div>

      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        {mode === "register" && (
          <>
            <label className="text-sm">
              Organization name
              <input
                className="mt-1 w-full rounded-lg border px-3 py-2"
                style={{ borderColor: "var(--glass-border)" }}
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                required
              />
            </label>
            <label className="text-sm">
              Industry
              <select
                className="mt-1 w-full rounded-lg border px-3 py-2"
                style={{ borderColor: "var(--glass-border)" }}
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
              >
                <option value="device">Medical device</option>
                <option value="drug">Drug manufacturer</option>
              </select>
            </label>
          </>
        )}

        <label className="text-sm">
          Email
          <input
            type="email"
            className="mt-1 w-full rounded-lg border px-3 py-2"
            style={{ borderColor: "var(--glass-border)" }}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label className="text-sm">
          Password
          <input
            type="password"
            className="mt-1 w-full rounded-lg border px-3 py-2"
            style={{ borderColor: "var(--glass-border)" }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </label>

        {error && <p style={{ color: "var(--severity-critical)" }}>{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded-lg border px-4 py-2 font-medium"
          style={{ borderColor: "var(--glass-border)" }}
        >
          {submitting ? "Please wait..." : mode === "login" ? "Log in" : "Create organization"}
        </button>
      </form>
    </GlassPanel>
  );
}
