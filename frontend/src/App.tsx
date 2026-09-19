import { NavLink, Route, Routes } from "react-router-dom";
import { Background } from "./components/Background";
import { RequireAuth } from "./components/RequireAuth";
import { useAuth } from "./context/AuthContext";
import { Dashboard } from "./pages/Dashboard";
import { FindingDetail } from "./pages/FindingDetail";
import { Login } from "./pages/Login";
import { Processing } from "./pages/Processing";
import { ReportExport } from "./pages/ReportExport";
import { Review } from "./pages/Review";
import { Upload } from "./pages/Upload";

const NAV_LINKS = [
  { to: "/", label: "Upload" },
  { to: "/findings", label: "Findings" },
  { to: "/review", label: "Review" },
  { to: "/report", label: "Report" },
];

function AppShell() {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen">
      <Background />
      <header className="mx-auto flex max-w-3xl items-center justify-between px-4 py-6">
        <span className="text-lg font-semibold">DeviationTrace</span>
        <nav className="flex gap-4 text-sm">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "font-semibold underline" : "")}
            >
              {link.label}
            </NavLink>
          ))}
          <button type="button" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>
      <main className="px-4 pb-16">
        <Routes>
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
