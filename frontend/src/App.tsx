import { Link, NavLink, Route, Routes } from "react-router-dom";
import { Background } from "./components/Background";
import { Logo } from "./components/Logo";
import { RequireAuth } from "./components/RequireAuth";
import { useAuth } from "./context/AuthContext";
import { AuditSimulation } from "./pages/AuditSimulation";
import { Dashboard } from "./pages/Dashboard";
import { FindingDetail } from "./pages/FindingDetail";
import { Login } from "./pages/Login";
import { Onboarding } from "./pages/Onboarding";
import { OrgChecklist } from "./pages/OrgChecklist";
import { Processing } from "./pages/Processing";
import { ReportExport } from "./pages/ReportExport";
import { Review } from "./pages/Review";
import { Upload } from "./pages/Upload";
import { VendorAudit } from "./pages/VendorAudit";

// Upload ("/") is the header's gradient call-to-action rather than a nav item.
const NAV_LINKS = [
  { to: "/onboarding", label: "New Company" },
  { to: "/findings", label: "Findings" },
  { to: "/review", label: "Review" },
  { to: "/report", label: "Report" },
  { to: "/org-checklist", label: "Checklist" },
  { to: "/audit-simulation", label: "Audit" },
  { to: "/vendor-audit", label: "Vendor Audit" },
];

function AppShell() {
  const { logout } = useAuth();

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
          <nav className="order-last -mx-1 flex w-full gap-1 overflow-x-auto text-sm lg:order-none lg:mx-0 lg:w-auto">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
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
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={logout}
              className="text-sm font-medium hover:underline"
              style={{ color: "#4b5563" }}
            >
              Log out
            </button>
            <NavLink to="/" end className="btn-primary px-4 py-2 text-sm">
              Upload document
            </NavLink>
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
                <Upload />
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
