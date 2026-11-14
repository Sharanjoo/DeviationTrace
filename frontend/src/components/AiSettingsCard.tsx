import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { PROVIDER_FIELDS, type AiSettings } from "../ai";

const INPUT = "mt-1.5 w-full rounded-lg border px-3 py-2 text-sm";
const INPUT_STYLE = { borderColor: "var(--glass-border)", color: "var(--text)" };
const muted = { color: "var(--text-muted)" };

/** Company profile section: whether AI assistance is on, which provider
 * the organization's data goes to, and how. Admins edit; others see. */
export function AiSettingsCard({ isAdmin }: { isAdmin: boolean }) {
  const [settings, setSettings] = useState<AiSettings | null>(null);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AiSettings>("/org/ai-settings")
      .then(setSettings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load AI settings."));
  }, []);

  if (!settings) return error ? <p style={{ color: "var(--severity-critical)" }}>{error}</p> : null;

  return (
    <section className="card p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">AI assistance</h2>
          <p className="mt-0.5 max-w-2xl text-sm" style={muted}>
            Optional. When on, members can ask an AI model to review the content of SOPs and deviation reports in an
            internal audit, choosing which sections are sent. Every request is logged with exactly what was sent.
          </p>
        </div>
        <span
          className="rounded-full px-2.5 py-1 text-xs font-semibold"
          style={
            settings.enabled
              ? { background: "var(--severity-resolved-tint)", color: "var(--severity-resolved)" }
              : { background: "#f1f5f9", color: "#475569" }
          }
        >
          {settings.enabled ? "On" : "Off"}
        </span>
      </div>

      {!editing && (
        <>
          <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs" style={muted}>
                Provider
              </dt>
              <dd className="font-semibold">{settings.providers[settings.provider]}</dd>
            </div>
            <div>
              <dt className="text-xs" style={muted}>
                Model
              </dt>
              <dd className="font-semibold">{settings.model}</dd>
            </div>
            <div>
              <dt className="text-xs" style={muted}>
                Remove names and IDs before sending
              </dt>
              <dd className="font-semibold">{settings.redact_identifiers ? "Yes, by default" : "No, by default"}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs" style={muted}>
            {PROVIDER_FIELDS[settings.provider].note}
          </p>
          {settings.updated_by && (
            <p className="mt-1 text-xs" style={muted}>
              Last changed by {settings.updated_by}
              {settings.updated_at && ` on ${new Date(settings.updated_at).toLocaleDateString()}`}
            </p>
          )}
          {isAdmin && (
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => setEditing(true)} className="btn-secondary px-3 py-1.5 text-xs">
                Change AI settings
              </button>
              <Link to="/company/ai-log" className="btn-secondary px-3 py-1.5 text-xs">
                AI activity log
              </Link>
            </div>
          )}
        </>
      )}

      {editing && (
        <AiSettingsForm
          settings={settings}
          onCancel={() => setEditing(false)}
          onSaved={(saved) => {
            setSettings(saved);
            setEditing(false);
          }}
        />
      )}
    </section>
  );
}

function AiSettingsForm({
  settings,
  onCancel,
  onSaved,
}: {
  settings: AiSettings;
  onCancel: () => void;
  onSaved: (settings: AiSettings) => void;
}) {
  const [form, setForm] = useState({
    enabled: settings.enabled,
    provider: settings.provider,
    model: settings.model,
    region: settings.region ?? "",
    project_id: settings.project_id ?? "",
    resource: settings.resource ?? "",
    redact_identifiers: settings.redact_identifiers,
  });
  // Write-only: blank keeps the stored key.
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fields = PROVIDER_FIELDS[form.provider];

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.put<AiSettings>("/org/ai-settings", { ...form, api_key: apiKey ? apiKey : null }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save AI settings.");
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="mt-4 flex flex-col gap-4">
      <label className="flex items-center gap-2 text-sm font-medium">
        <input
          type="checkbox"
          className="h-4 w-4 accent-blue-600"
          checked={form.enabled}
          onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
        />
        Turn on AI assistance for this organization
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-medium">
          Provider (where your data goes)
          <select
            className={INPUT}
            style={INPUT_STYLE}
            value={form.provider}
            onChange={(e) => setForm({ ...form, provider: e.target.value as AiSettings["provider"] })}
          >
            {Object.entries(settings.providers).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          {form.provider === "foundry" ? "Deployment name" : "Model"}
          <input className={INPUT} style={INPUT_STYLE} value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} required />
        </label>
        {fields.region && (
          <label className="text-sm font-medium">
            {form.provider === "vertex" ? "Region (e.g. global, us-east5)" : "AWS region (e.g. us-east-1)"}
            <input className={INPUT} style={INPUT_STYLE} value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
          </label>
        )}
        {fields.project && (
          <label className="text-sm font-medium">
            Google Cloud project ID
            <input className={INPUT} style={INPUT_STYLE} value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} />
          </label>
        )}
        {fields.resource && (
          <label className="text-sm font-medium">
            Foundry resource name
            <input className={INPUT} style={INPUT_STYLE} value={form.resource} onChange={(e) => setForm({ ...form, resource: e.target.value })} />
          </label>
        )}
        {fields.apiKey && (
          <label className="text-sm font-medium">
            API key {settings.api_key_set && <span className="font-normal" style={muted}>(saved; leave blank to keep)</span>}
            <input
              type="password"
              autoComplete="off"
              className={INPUT}
              style={INPUT_STYLE}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={settings.api_key_set ? "••••••••  (stored encrypted)" : "Paste the API key"}
            />
          </label>
        )}
      </div>
      <p className="text-xs" style={muted}>
        {fields.note}
      </p>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          className="h-4 w-4 accent-blue-600"
          checked={form.redact_identifiers}
          onChange={(e) => setForm({ ...form, redact_identifiers: e.target.checked })}
        />
        By default, remove names, emails, phone numbers and employee IDs before sending (can be changed per review)
      </label>

      {error && <p className="text-sm" style={{ color: "var(--severity-critical)" }}>{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={saving} className="btn-primary px-4 py-2 text-sm">
          {saving ? "Saving..." : "Save AI settings"}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary px-4 py-2 text-sm">
          Cancel
        </button>
      </div>
    </form>
  );
}
