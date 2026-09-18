import { NavLink, Route, Routes } from "react-router-dom";
import { Background } from "./components/Background";
import { Dashboard } from "./pages/Dashboard";
import { FindingDetail } from "./pages/FindingDetail";
import { Processing } from "./pages/Processing";
import { ReportExport } from "./pages/ReportExport";
import { Upload } from "./pages/Upload";

const NAV_LINKS = [
  { to: "/", label: "Upload" },
  { to: "/processing", label: "Processing" },
  { to: "/findings", label: "Findings" },
  { to: "/findings/detail", label: "Finding detail" },
  { to: "/report", label: "Report" },
];

function App() {
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
        </nav>
      </header>
      <main className="px-4 pb-16">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/processing" element={<Processing />} />
          <Route path="/findings" element={<Dashboard />} />
          <Route path="/findings/detail" element={<FindingDetail />} />
          <Route path="/report" element={<ReportExport />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
