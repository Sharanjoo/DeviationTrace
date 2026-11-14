/** Types and labels for the company profile and its members. */

export interface Member {
  id: string;
  full_name: string | null;
  email: string;
  role: "admin" | "member" | "viewer";
  created_at: string;
}

export interface OrgProfile {
  id: string;
  name: string;
  industry: string;
  created_at: string;
  onboarded_at: string | null;
  scope_label: string | null;
  member_count: number;
  you: Member;
}

export const ROLES: { value: Member["role"]; label: string; description: string }[] = [
  { value: "admin", label: "Admin", description: "In charge: manages members, roles and the company profile." },
  { value: "member", label: "Member", description: "Does the audit work: uploads, runs simulations and vendor audits." },
  { value: "viewer", label: "Viewer", description: "Read-only: can see results and download reports." },
];
export const ROLE_LABELS: Record<string, string> = Object.fromEntries(ROLES.map((r) => [r.value, r.label]));

export function displayName(member: Pick<Member, "full_name" | "email">): string {
  return member.full_name || member.email;
}

export function initials(name: string): string {
  const words = name.trim().split(/[\s@.]+/).filter(Boolean);
  return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] ?? "?").slice(0, 2)).toUpperCase();
}
