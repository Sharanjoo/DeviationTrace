export const TRIAGE_LABELS = {
  confirmed: "Confirmed",
  false_positive: "False positive",
  needs_sme: "Needs SME",
} as const;

export type TriageDecisionValue = keyof typeof TRIAGE_LABELS;
