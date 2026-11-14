import { useOnboarding } from "../context/OnboardingContext";
import { GlassPanel } from "./GlassPanel";

const INDUSTRY_LABELS: Record<string, string> = { device: "Medical device", drug: "Drug manufacturer" };

/** The company details remembered from onboarding, shown in place of the
 * setup page once it's done. */
export function CompanyProfile() {
  const { status } = useOnboarding();
  if (!status?.completed) return null;

  const setUpOn = status.onboarded_at
    ? new Date(status.onboarded_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : null;
  const fields = [
    { label: "Company", value: status.org_name, wide: false },
    { label: "Industry", value: INDUSTRY_LABELS[status.industry] ?? status.industry, wide: false },
    { label: "Scope", value: status.scope_label ?? "Standard checklist", wide: true },
    ...(setUpOn ? [{ label: "Set up", value: setUpOn, wide: false }] : []),
  ];

  return (
    <GlassPanel className="!p-5">
      <p className="eyebrow">Company profile</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-5">
        {fields.map((f) => (
          <div key={f.label} className={f.wide ? "col-span-2" : ""}>
            <dt className="text-xs" style={{ color: "var(--text-muted)" }}>
              {f.label}
            </dt>
            <dd className="mt-0.5 font-semibold">{f.value}</dd>
          </div>
        ))}
      </dl>
    </GlassPanel>
  );
}
