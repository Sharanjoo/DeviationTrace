/** Shared types and helpers for vendors and vendor audits. */

export interface VendorAuditSummary {
  id: string;
  audit_number: number;
  audit_code: string;
  vendor_id: string;
  vendor_name: string;
  vendor_category: string;
  audit_date: string | null;
  auditor_name: string | null;
  auditor_employee_id: string | null;
  notes: string | null;
  created_at: string;
  document_id: string;
  document_title: string;
  document_status: string;
  processing_error: string | null;
  missing: number;
  partial: number;
  satisfied: number;
  total: number;
}

export interface VendorAuditFindingRow {
  id: string;
  requirement_name: string;
  citation: string;
  requirement_text: string;
  status: "missing" | "partial" | "satisfied";
  severity: string;
  explanation: string;
}

export interface VendorAuditDetail extends VendorAuditSummary {
  findings: VendorAuditFindingRow[];
}

export interface Vendor {
  id: string;
  name: string;
  vendor_category: string;
  contact_name: string | null;
  contact_email: string | null;
  notes: string | null;
  created_at: string;
  audit_count: number;
  latest_audit: VendorAuditSummary | null;
}

export interface VendorDetail extends Vendor {
  audits: VendorAuditSummary[];
}

export interface UnassignedReport {
  id: string;
  title: string;
  vendor_category: string | null;
  status: string;
  uploaded_at: string;
}

export function standardsMet(audit: Pick<VendorAuditSummary, "satisfied" | "total">): number | null {
  return audit.total ? Math.round((audit.satisfied / audit.total) * 100) : null;
}

export function vendorCounts(audit: VendorAuditSummary): Record<string, number> {
  return { missing: audit.missing, partial: audit.partial, satisfied: audit.satisfied };
}

/** The audit's date if given, otherwise when it was recorded. */
export function vendorAuditDate(audit: VendorAuditSummary): string {
  if (audit.audit_date) {
    const [y, m, d] = audit.audit_date.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }
  return new Date(audit.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

/** "VEN-RM-2026-008_Acme_Report.docx" -> "VEN-RM-2026-008 Acme Report" */
export function displayFileName(filename: string): string {
  return filename.replace(/\.(docx|pdf|txt)$/i, "").replace(/_/g, " ");
}
