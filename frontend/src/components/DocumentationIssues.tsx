import { DEPARTMENT_NAMES, type DocumentationIssue, type RunDocumentationIssue } from "../simulationRuns";
import { StatusIcon } from "./CheckResults";

const muted = { color: "var(--text-muted)" };

const KIND: Record<DocumentationIssue["kind"], { label: string; tone: "bad" | "warn" }> = {
  missing_signature: { label: "Missing signature", tone: "bad" },
  missing_stamp: { label: "Missing stamp", tone: "bad" },
  missing_date: { label: "Missing date", tone: "bad" },
  missing_entry: { label: "Blank entry", tone: "warn" },
  placeholder: { label: "Unfilled placeholder", tone: "warn" },
  scanned: { label: "Scanned: check by hand", tone: "warn" },
};

function displayTitle(filename: string): string {
  return filename.replace(/\.(docx|pdf|txt)$/i, "").replace(/_/g, " ");
}

/** Documentation completeness (Good Documentation Practice): blank
 * signatures, stamps, dates and entries, and unfilled template text.
 * Pass `documentTitle` for a single document (vendor audit), or run issues
 * (which carry their own document titles) to group by document. */
export function DocumentationIssues({
  issues,
  documentTitle,
  emptyText = "No blank signatures, stamps, dates or entries, and no unfilled placeholders, were found.",
}: {
  issues: (DocumentationIssue | RunDocumentationIssue)[];
  documentTitle?: string;
  emptyText?: string;
}) {
  const groups = new Map<string, (DocumentationIssue | RunDocumentationIssue)[]>();
  for (const issue of issues) {
    const title = documentTitle ?? ("document_title" in issue ? issue.document_title : "Document");
    if (!groups.has(title)) groups.set(title, []);
    groups.get(title)!.push(issue);
  }
  const signatures = issues.filter((i) => ["missing_signature", "missing_stamp"].includes(i.kind)).length;
  const dates = issues.filter((i) => i.kind === "missing_date").length;
  const other = issues.length - signatures - dates;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Documentation check</p>
          <h2 className="mt-1 text-2xl font-bold">Signatures, dates and blank fields</h2>
          <p className="mt-1 max-w-3xl text-sm" style={muted}>
            Sign-off fields and template text left blank, the kind of Good Documentation Practice gap an auditor spots
            first. Scanned documents can't be read yet, so they're flagged for a manual check.
          </p>
        </div>
        {issues.length > 0 && (
          <div className="flex gap-3 text-sm">
            <Count label="Signatures / stamps" value={signatures} />
            <Count label="Dates" value={dates} />
            <Count label="Other blanks" value={other} />
          </div>
        )}
      </div>

      {issues.length === 0 && (
        <div className="card flex items-center gap-3 p-5 text-sm">
          <StatusIcon tone="good" size={22} />
          {emptyText}
        </div>
      )}

      {[...groups.entries()].map(([title, rows]) => {
        const first = rows[0];
        return (
          <section key={title} className="card overflow-hidden">
            <header className="border-b px-5 py-4" style={{ borderColor: "var(--glass-border)" }}>
              <h3 className="text-lg font-semibold [overflow-wrap:anywhere]">{displayTitle(title)}</h3>
              <p className="mt-0.5 text-sm" style={muted}>
                {"department" in first ? `${DEPARTMENT_NAMES[first.department] ?? first.department} · ` : ""}
                {rows.length} issue{rows.length === 1 ? "" : "s"}
              </p>
            </header>
            <ul className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
              {rows.map((issue) => {
                const kind = KIND[issue.kind] ?? { label: issue.kind, tone: "warn" as const };
                return (
                  <li key={issue.id} className="flex gap-4 px-5 py-3.5" style={{ borderColor: "var(--glass-border)" }}>
                    <StatusIcon tone={kind.tone} size={22} className="mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">
                        {kind.label}
                        {issue.kind !== "scanned" && <span className="font-normal">: {issue.field}</span>}
                        {issue.confidence === "check" && (
                          <span className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase" style={{ background: "#f1f5f9", color: "#475569" }}>
                            Possibly: page has images
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-sm [overflow-wrap:anywhere]" style={muted}>
                        {issue.location && <span className="font-medium">{issue.location}: </span>}
                        <span className="font-mono text-xs">{issue.context}</span>
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </section>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div className="card px-4 py-2 text-center">
      <p className="text-xl font-bold" style={{ color: value ? "var(--severity-critical)" : "var(--text)" }}>
        {value}
      </p>
      <p className="text-xs" style={muted}>
        {label}
      </p>
    </div>
  );
}
