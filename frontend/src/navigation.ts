/** App navigation: one top-level link per area, with sub-tabs inside the
 * areas that have several pages. (SOP and deviation report checking is part
 * of the internal audit: SOPs and deviation reports are added in step 2 of a
 * simulation and content-checked when it runs. The older standalone
 * Findings / Review / Report pages are no longer linked.)
 * A "match" entry is a path prefix; a leading "=" means that exact path only. */

export interface NavTab {
  label: string;
  to: string;
  match: string[];
}

export interface NavSection {
  key: string;
  label: string;
  to: string;
  match: string[];
  tabs: NavTab[];
}

export const NAV_SECTIONS: NavSection[] = [
  { key: "home", label: "Home", to: "/", match: ["=/"], tabs: [] },
  {
    key: "internal",
    label: "Internal audit",
    to: "/audit-simulation/runs",
    match: ["/audit-simulation", "/org-checklist"],
    tabs: [
      { label: "All audits", to: "/audit-simulation/runs", match: ["/audit-simulation/runs", "/audit-simulation/new"] },
      { label: "Latest results", to: "/audit-simulation", match: ["=/audit-simulation"] },
      { label: "Checklist", to: "/org-checklist", match: ["/org-checklist"] },
      { label: "Reports", to: "/audit-simulation/reports", match: ["/audit-simulation/reports"] },
    ],
  },
  { key: "vendor", label: "Vendor audit", to: "/vendor-audit", match: ["/vendor-audit"], tabs: [] },
];

export function pathMatches(pathname: string, patterns: string[]): boolean {
  return patterns.some((p) =>
    p.startsWith("=") ? pathname === p.slice(1) : pathname === p || pathname.startsWith(`${p}/`),
  );
}

/** Most specific tab wins (e.g. /audit-simulation/reports is Reports, not
 * Latest results). */
export function activeTab(section: NavSection, pathname: string): NavTab | undefined {
  return section.tabs
    .filter((t) => pathMatches(pathname, t.match))
    .sort((a, b) => Math.max(...b.match.map((m) => m.length)) - Math.max(...a.match.map((m) => m.length)))[0];
}
