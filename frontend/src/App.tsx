import { Link, Route, Routes, useLocation } from "react-router-dom";
import { AccountMenu } from "./components/AccountMenu";
import { Background } from "./components/Background";
import { Logo } from "./components/Logo";
import { RequireAuth } from "./components/RequireAuth";
import { useOnboarding } from "./context/OnboardingContext";
import { activeTab, NAV_SECTIONS, pathMatches } from "./navigation";
import { AuditReports } from "./pages/AuditReports";
import { AuditSimulation } from "./pages/AuditSimulation";
import { CompanyProfile } from "./pages/CompanyProfile";
import { Dashboard } from "./pages/Dashboard";
import { DepartmentChecklist } from "./pages/DepartmentChecklist";
import { FindingDetail } from "./pages/FindingDetail";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { NewAudit } from "./pages/NewAudit";
import { Onboarding } from "./pages/Onboarding";
import { OrgChecklist } from "./pages/OrgChecklist";
import { Processing } from "./pages/Processing";
import { ReportExport } from "./pages/ReportExport";
import { SimulationRunDetail } from "./pages/SimulationRunDetail";
import { SimulationRuns } from "./pages/SimulationRuns";
import { Review } from "./pages/Review";
import { Upload } from "./pages/Upload";
import { VendorAudit } from "./pages/VendorAudit";
import { VendorAuditDetailPage } from "./pages/VendorAuditDetailPage";
import { VendorDetailPage } from "./pages/VendorDetailPage";

// Onboarding isn't in the nav: it's shown automatically, once, before
// anything else (see RequireAuth), and never again after it's done.
// Log out lives in the AccountMenu on the right, away from these links.
// Sections and their sub-tabs are defined in navigation.ts.

const linkStyle = (active: boolean) =>
  active ? { background: "var(--tint-blue)", color: "var(--brand-blue-text)" } : { color: "#4b5563" };

function AppShell() {
  const { status } = useOnboarding();
  const { pathname } = useLocation();
  // Until onboarding is done, the only thing to do is onboarding, so the
  // header shows just the logo and the account menu.
  const showAppNav = status?.completed === true;
  const section = NAV_SECTIONS.find((s) => pathMatches(pathname, s.match));
  const tab = section ? activeTab(section, pathname) : undefined;

  return (
    <div className="min-h-screen">
      <Background />
      <header
        className="sticky top-0 z-20 border-b backdrop-blur"
        style={{ background: "rgba(255,255,255,0.92)", borderColor: "var(--glass-border)" }}
      >
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-4">
          <Link to="/" aria-label="DeviationTrace home">
            <Logo />
          </Link>
          {showAppNav && (
            <nav
              aria-label="Main"
              className="order-last -mx-1 flex w-full gap-1 overflow-x-auto text-sm lg:order-none lg:mx-0 lg:w-auto"
            >
              {NAV_SECTIONS.map((s) => {
                const active = s.key === section?.key;
                return (
                  <Link
                    key={s.key}
                    to={s.to}
                    aria-current={active ? "page" : undefined}
                    className="shrink-0 rounded-lg px-3 py-2 font-medium transition-colors hover:bg-slate-100"
                    style={linkStyle(active)}
                  >
                    {s.label}
                  </Link>
                );
              })}
            </nav>
          )}
          <AccountMenu />
        </div>
        {showAppNav && section && section.tabs.length > 0 && (
          <div className="border-t" style={{ borderColor: "var(--glass-border)" }}>
            <nav aria-label={section.label} className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 text-sm">
              {section.tabs.map((t) => {
                const active = t === tab;
                return (
                  <Link
                    key={t.to}
                    to={t.to}
                    aria-current={active ? "page" : undefined}
                    className="shrink-0 border-b-2 px-3 py-2.5 font-medium transition-colors"
                    style={{
                      borderColor: active ? "var(--brand-blue)" : "transparent",
                      color: active ? "var(--brand-blue-text)" : "#4b5563",
                    }}
                  >
                    {t.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        )}
      </header>
      <main className="px-4 pt-10 pb-20">
        <Routes>
          <Route
            path="/onboarding"
            element={
              <RequireAuth>
                <Onboarding />
              </RequireAuth>
            }
          />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Home />
              </RequireAuth>
            }
          />
          <Route
            path="/upload"
            element={
              <RequireAuth>
                <Upload />
              </RequireAuth>
            }
          />
          <Route
            path="/audit-simulation/new"
            element={
              <RequireAuth>
                <NewAudit />
              </RequireAuth>
            }
          />
          <Route
            path="/audit-simulation/runs/:runId/edit"
            element={
              <RequireAuth>
                <NewAudit />
              </RequireAuth>
            }
          />
          <Route
            path="/audit-simulation/reports"
            element={
              <RequireAuth>
                <AuditReports />
              </RequireAuth>
            }
          />
          <Route
            path="/audit-simulation/runs"
            element={
              <RequireAuth>
                <SimulationRuns />
              </RequireAuth>
            }
          />
          <Route
            path="/audit-simulation/runs/:runId"
            element={
              <RequireAuth>
                <SimulationRunDetail />
              </RequireAuth>
            }
          />
          <Route
            path="/processing/:documentId"
            element={
              <RequireAuth>
                <Processing />
              </RequireAuth>
            }
          />
          <Route
            path="/findings"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/findings/:id"
            element={
              <RequireAuth>
                <FindingDetail />
              </RequireAuth>
            }
          />
          <Route
            path="/review"
            element={
              <RequireAuth>
                <Review />
              </RequireAuth>
            }
          />
          <Route
            path="/report"
            element={
              <RequireAuth>
                <ReportExport />
              </RequireAuth>
            }
          />
          <Route
            path="/company"
            element={
              <RequireAuth>
                <CompanyProfile />
              </RequireAuth>
            }
          />
          <Route
            path="/org-checklist"
            element={
              <RequireAuth>
                <OrgChecklist />
              </RequireAuth>
            }
          />
          <Route
            path="/org-checklist/:department"
            element={
              <RequireAuth>
                <DepartmentChecklist />
              </RequireAuth>
            }
          />
          <Route
            path="/audit-simulation"
            element={
              <RequireAuth>
                <AuditSimulation />
              </RequireAuth>
            }
          />
          <Route
            path="/vendor-audit"
            element={
              <RequireAuth>
                <VendorAudit />
              </RequireAuth>
            }
          />
          <Route
            path="/vendor-audit/vendors/:vendorId"
            element={
              <RequireAuth>
                <VendorDetailPage />
              </RequireAuth>
            }
          />
          <Route
            path="/vendor-audit/audits/:auditId"
            element={
              <RequireAuth>
                <VendorAuditDetailPage />
              </RequireAuth>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Routes>
      {/* Login owns its own full-screen layout (background image, centered
          card) rather than sharing the authenticated app's header/nav chrome. */}
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={<AppShell />} />
    </Routes>
  );
}

export default App;
