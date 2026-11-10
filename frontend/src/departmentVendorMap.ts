// Which department is responsible for auditing which vendor category.
// Not stored in the backend — purely a navigation/grouping concern, so a
// static frontend mapping is enough: it lets the Org Checklist page surface
// "the vendor categories this department owns" and lets the Vendor Audit
// page be entered pre-filtered from there, without a schema/migration
// change to the (still global) VendorStandard library.
export const DEPARTMENT_BY_VENDOR_CATEGORY: Record<string, string> = {
  raw_material_supplier: "qc",
  calibration_test_service: "qc",
  contract_manufacturer: "qa",
  sterilization_service: "manufacturing",
  packaging_component_supplier: "manufacturing",
};

export const VENDOR_CATEGORIES_BY_DEPARTMENT: Record<string, string[]> = Object.entries(
  DEPARTMENT_BY_VENDOR_CATEGORY,
).reduce<Record<string, string[]>>((acc, [category, department]) => {
  (acc[department] ??= []).push(category);
  return acc;
}, {});

export const DEPARTMENT_LABELS: Record<string, string> = {
  qc: "QC",
  qa: "QA",
  utilities: "Utilities",
  manufacturing: "Manufacturing",
  engineering: "Engineering",
};

export const VENDOR_CATEGORY_LABELS: Record<string, string> = {
  raw_material_supplier: "Raw material supplier",
  contract_manufacturer: "Contract manufacturer",
  calibration_test_service: "Calibration / test service",
  sterilization_service: "Sterilization service",
  packaging_component_supplier: "Packaging component supplier",
};
