"""Generate the synthetic vendor audit report documents used for the
Module 2 (Vendor Audit Cross-Check) SME review session.

Run from backend/: python -m app.seed.vendor_audit_demo_documents
Writes .docx files to <repo root>/demo_documents/.

Every document is fictional and says so in its title block. Unlike the
Module 1 department demo set (where an outcome depends on whether a whole
document exists), each document here produces all three outcomes on its
own: one passage gives full phrase coverage for a standard ("satisfied"),
one gives partial coverage in plain English without the curated phrase
("partial" — a realistic false negative for the SME to note), and one
addresses none of a standard's phrases at all ("missing").
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx import Document as DocxDocument

from app.seed.demo_documents import DEFAULT_OUTPUT_DIR, SYNTHETIC_NOTICE

_FIXED_TIMESTAMP = datetime(2026, 1, 1)


@dataclass(frozen=True)
class VendorAuditDemoDocument:
    filename: str
    vendor_category: str
    title_block: tuple[str, ...]
    sections: tuple[tuple[str, tuple[str, ...]], ...]


VENDOR_AUDIT_DEMO_DOCUMENTS: tuple[VendorAuditDemoDocument, ...] = (
    # raw_material_supplier — satisfied (Certificate of Analysis), partial
    # (Supplier Qualification Assessment), missing (Change Notification Agreement).
    VendorAuditDemoDocument(
        filename="VEN-RM-2026-008_Acme_Excipient_Supplier_Audit_Report.docx",
        vendor_category="raw_material_supplier",
        title_block=(
            "VEN-RM-2026-008 Vendor audit report - Excipient Supplier Co. (raw material)",
            "Audit date 2026-02-14 | Auditor: Acme Pharma Devices QA | Vendor: Excipient Supplier Co.",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Certificate of Analysis",
                (
                    "Excipient Supplier Co. provided a certificate of analysis for every lot shipped in "
                    "2025 and 2026, including lot-specific test results for identity, assay, and microbial "
                    "limits, cross-checked against Acme's incoming specification before release to inventory.",
                ),
            ),
            (
                "Vendor Qualification Status",
                (
                    "The vendor appears on Acme's approved supplier list, having passed an on-site quality "
                    "assessment in 2024. The audit could not confirm whether that assessment was formally "
                    "repeated after the vendor's 2025 facility relocation, since no updated qualification "
                    "record was produced during the audit.",
                ),
            ),
            (
                "Change Communication",
                (
                    "No documentation was provided describing how the vendor communicates changes to raw "
                    "material formulation, manufacturing site, or specifications to Acme in advance of "
                    "implementation.",
                ),
            ),
        ),
    ),
    # contract_manufacturer — satisfied (Quality Agreement), partial (Batch
    # Release Procedure), missing (Deviation Reporting to Client).
    VendorAuditDemoDocument(
        filename="VEN-CM-2026-014_Bright_Path_Sterile_Fill_CMO_Audit_Report.docx",
        vendor_category="contract_manufacturer",
        title_block=(
            "VEN-CM-2026-014 Vendor audit report - Bright Path Sterile Fill (contract manufacturer)",
            "Audit date 2026-03-02 | Auditor: Acme Pharma Devices QA | Vendor: Bright Path Sterile Fill LLC",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Quality Agreement",
                (
                    "A current quality agreement between Acme Pharma Devices and Bright Path Sterile Fill "
                    "defines roles and responsibilities for batch disposition, change control, and deviation "
                    "escalation, and was last reviewed in January 2026.",
                ),
            ),
            (
                "Batch Release",
                (
                    "Bright Path performs release testing on every batch before shipment, per its internal "
                    "specifications. The audit could not confirm a formal, written procedure exists "
                    "describing who holds final release authority for each batch.",
                ),
            ),
            (
                "Escalation to Client",
                (
                    "No records were available describing how manufacturing deviations occurring at the "
                    "Bright Path site are escalated to Acme, or within what timeframe Acme is informed of "
                    "them.",
                ),
            ),
        ),
    ),
    # sterilization_service — satisfied (Validated Sterilization Cycle),
    # partial (Biological Indicator Results), missing (Dose Audit / Bioburden Report).
    VendorAuditDemoDocument(
        filename="VEN-STR-2026-021_Clearwave_EtO_Sterilization_Audit_Report.docx",
        vendor_category="sterilization_service",
        title_block=(
            "VEN-STR-2026-021 Vendor audit report - Clearwave EtO Sterilization (sterilization service)",
            "Audit date 2026-03-19 | Auditor: Acme Pharma Devices QA | Vendor: Clearwave Sterilization Services",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "Sterilization Cycle Validation",
                (
                    "Clearwave's EtO sterilization cycle for lot 26-090 was run per its validated cycle "
                    "validation protocol EO-VAL-07, confirming exposure parameters met the qualified "
                    "sterilization cycle envelope for this device family.",
                ),
            ),
            (
                "Biological Indicators",
                (
                    "Biological indicator strips were placed at the qualified worst-case locations for this "
                    "load and returned negative growth after incubation. The report did not specify the "
                    "spore organism or population used on the indicators for this run.",
                ),
            ),
            (
                "Additional Verification",
                (
                    "No pre-sterilization microbial load testing or periodic exposure re-verification "
                    "documentation was included in the audit package for this vendor.",
                ),
            ),
        ),
    ),
)


def build_document(demo: VendorAuditDemoDocument, output_dir: Path) -> Path:
    doc = DocxDocument()
    core = doc.core_properties
    core.author = core.last_modified_by = "DeviationTrace demo generator"
    core.created = core.modified = _FIXED_TIMESTAMP
    core.title = demo.filename.removesuffix(".docx")

    doc.add_heading(demo.title_block[0], level=0)
    for line in demo.title_block[1:]:
        doc.add_paragraph(line)
    for heading, paragraphs in demo.sections:
        doc.add_heading(heading, level=1)
        for paragraph in paragraphs:
            doc.add_paragraph(paragraph)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / demo.filename
    doc.save(path)
    return path


def build_all(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    return [build_document(demo, output_dir) for demo in VENDOR_AUDIT_DEMO_DOCUMENTS]


if __name__ == "__main__":
    for written in build_all():
        print(f"Wrote {written}")
