/** Departments as shown on the checklist pages, with their tile styling. */

export interface ChecklistDepartment {
  value: string;
  label: string;
  name: string;
  blurb: string;
  icon: string;
  tint: string;
  color: string;
}

export interface EffectiveChecklistItem {
  id: string;
  department: string;
  item_name: string;
  citation: string;
  requirement_text: string;
  match_phrases: string[];
  is_custom: boolean;
  is_excluded: boolean;
}

export const CHECKLIST_DEPARTMENTS: ChecklistDepartment[] = [
  {
    value: "qc",
    label: "QC",
    name: "Quality Control",
    blurb: "Testing, calibration and out-of-spec records.",
    // flask
    icon: "M9 3h6M10 3v6L4.5 18.5A1.5 1.5 0 005.8 21h12.4a1.5 1.5 0 001.3-2.5L14 9V3M7 15h10",
    tint: "var(--tint-blue)",
    color: "var(--brand-blue)",
  },
  {
    value: "qa",
    label: "QA",
    name: "Quality Assurance",
    blurb: "CAPA, internal audits and management review.",
    // shield check
    icon: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10zM9 12l2 2 4-4",
    tint: "var(--tint-violet)",
    color: "var(--brand-violet)",
  },
  {
    value: "utilities",
    label: "Utilities",
    name: "Utilities",
    blurb: "Water, HVAC and utility monitoring.",
    // bolt
    icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    tint: "var(--tint-blue)",
    color: "var(--brand-blue)",
  },
  {
    value: "manufacturing",
    label: "Manufacturing",
    name: "Manufacturing",
    blurb: "Device history, process validation and maintenance.",
    // factory
    icon: "M2 20h20M4 20V10l5 3V10l5 3V6l6 4v10M8 16h1M12 16h1M16 16h1",
    tint: "var(--tint-violet)",
    color: "var(--brand-violet)",
  },
  {
    value: "engineering",
    label: "Engineering",
    name: "Engineering",
    blurb: "Design history, risk management and change control.",
    // pencil
    icon: "M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4 12.5-12.5z",
    tint: "var(--tint-blue)",
    color: "var(--brand-blue)",
  },
];
