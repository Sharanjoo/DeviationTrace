import { Link, NavLink, Route, Routes } from "react-router-dom";
import { Background } from "./components/Background";
import { Logo } from "./components/Logo";
import { RequireAuth } from "./components/RequireAuth";
import { useAuth } from "./context/AuthContext";
import { useOnboarding } from "./context/OnboardingContext";
import { AuditSimulation } from "./pages/AuditSimulation";
import { Dashboard } from "./pages/Dashboard";
import { FindingDetail } from "./pages/FindingDetail";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Onboarding } from "./pages/Onboarding";
import { OrgChecklist } from "./pages/OrgChecklist";
import { Processing } from "./pages/Processing";
import { ReportExport } from "./pages/ReportExport";
import { SimulationRunDetail } from "./pages/SimulationRunDetail";
import { SimulationRuns } from "./pages/SimulationRuns";
import { Review } from "./pages/Review";
import { Upload } from "./pages/Upload";
import { VendorAudit } from "./pages/VendorAudit";

// Upload ("/upload") is the header's gradient call-to-action rather than a nav item.
// Onboarding isn't in the nav: it's shown automatically, once, before
// anything else (see RequireAuth), and never again after it's done.
const NAV_LINKS = [
  { to: "/", label: "Home" },
  { to: "/findings", label: "Findings" },
  { to: "/review", label: "Review" },
  { to: "/report", label: "Report" },
  { to: "/org-checklist", label: "Checklist" },
  { to: "/audit-simulation", label: "Audit" },
  { to: "/vendor-audit", label: "Vendor Audit" },
];

function AppShell() {
  const { logout } = useAuth();
  const { status } = useOnboarding();
  // Until onboarding is done, the only thing to do is onboarding, so the
  // header shows just the logo and Log out.
  const showAppNav = status?.completed === true;

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
          <nav className="order-last -mx-1 flex w-full gap-1 overflow-x-auto text-sm lg:order-none lg:mx-0 lg:w-auto">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                className="shrink-0 rounded-lg px-3 py-2 font-medium transition-colors hover:bg-slate-100"
                style={({ isActive }) =>
                  isActive
                    ? { background: "var(--tint-blue)", color: "var(--brand-blue-text)" }
                    : { color: "#4b5563" }
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          )}
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={logout}
              className="text-sm font-medium hover:underline"
              style={{ color: "#4b5563" }}
            >
              Log out
            </button>
            {showAppNav && (
              <NavLink to="/upload" className="btn-primary px-4 py-2 text-sm">
                Upload document
              </NavLink>
            )}
          </div>
        </div>
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
            path="/org-checklist"
            element={
              <RequireAuth>
                <OrgChecklist />
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
