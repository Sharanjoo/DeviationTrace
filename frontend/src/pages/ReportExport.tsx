import { GlassPanel } from "../components/GlassPanel";

export function ReportExport() {
  return (
    <GlassPanel className="mx-auto max-w-2xl text-center">
      <h1 className="text-2xl font-semibold">Report export</h1>
      <p className="mt-2" style={{ color: "var(--text-muted)" }}>
        Calls <code>GET /reports/&#123;org_id&#125;/export</code>, which returns 501 until
        Milestone 4 builds the PDF summary for the SME review session.
      </p>
    </GlassPanel>
  );
}
