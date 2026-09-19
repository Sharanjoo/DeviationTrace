"""Generate the synthetic documents used for SME review sessions.

Run from backend/: python -m app.seed.demo_documents
Writes .docx files to <repo root>/demo_documents/.

Every document is fictional and says so in its title block. The wording is
deliberately tuned to the rule-based engine: each clause phrase sits inside a
single paragraph, and a few passages satisfy the regulation in plain English
without using the curated phrase, so the SME has real false positives to triage.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx import Document as DocxDocument

SYNTHETIC_NOTICE = "SYNTHETIC DEMONSTRATION DOCUMENT - NOT A REAL RECORD. Prepared for DeviationTrace SME review sessions."

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "demo_documents"


@dataclass(frozen=True)
class DemoDocument:
    filename: str
    document_type: str  # sop | deviation
    process_area: str  # deviation_handling | capa
    title_block: tuple[str, ...]
    sections: tuple[tuple[str, tuple[str, ...]], ...]


DEMO_DOCUMENTS: tuple[DemoDocument, ...] = (
    DemoDocument(
        filename="SOP-QA-014_Control_of_Nonconforming_Product.docx",
        document_type="sop",
        process_area="deviation_handling",
        title_block=(
            "SOP-QA-014 Control of Nonconforming Product",
            "Version 3.0 | Effective 2026-01-15 | Owner: Quality Assurance | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "1. Purpose",
                (
                    "This procedure defines how the site controls product that does not conform to specified "
                    "requirements. It establishes the procedure to define the controls, responsibilities and "
                    "authorities for the control of nonconforming product, from first detection through final "
                    "disposition.",
                ),
            ),
            (
                "2. Scope",
                (
                    "This SOP applies to raw materials, in-process material, finished product and returned "
                    "product at all manufacturing and packaging areas of the Acme Pharma Devices site.",
                ),
            ),
            (
                "3. Responsibilities",
                (
                    "Department managers are responsible for stopping work and notifying Quality Assurance on "
                    "the same shift when nonconforming product is suspected.",
                    "The quality control unit is responsible for reviewing every deviation investigation and has "
                    "the authority to approve or reject dispositions, procedure changes and batch release "
                    "decisions.",
                ),
            ),
            (
                "4. Procedure",
                (
                    "Any employee who detects suspected nonconforming product shall stop work and complete a "
                    "deviation form. Quality Assurance shall confirm the identification of nonconforming product "
                    "by lot number, quantity and location and enter it in the deviation log.",
                    "Confirmed nonconforming product shall be tagged and moved to the quarantine area to ensure "
                    "segregation of nonconforming product from released stock.",
                    "Quality Assurance shall decide whether an investigation is needed. The deviation record "
                    "shall state whether an investigation was conducted and, where none was performed, justify "
                    "that decision.",
                    "Once QA has notified the responsible department head of the nonconformance, the need for an "
                    "investigation and its rationale shall be documented in the deviation record.",
                    "Every unexplained discrepancy shall be thoroughly investigated, and the record shall include "
                    "the conclusions and follow-up actions.",
                    "Disposition of nonconforming product shall be assigned by Quality Assurance. Disposition may "
                    "include action to eliminate the nonconformity through rework or reprocessing, authorizing "
                    "use under concession with documented approval of the quality control unit, or action to "
                    "preclude original intended use by scrapping the material.",
                    "Deviations that originate from a customer complaint shall be entered in the complaint file "
                    "and handled under the complaint handling procedure, SOP-QA-031.",
                    "Quality Assurance shall assess whether a complaint describes a serious and unexpected event. "
                    "The investigation and its findings shall be recorded in the deviation record.",
                    "Trends in deviations feed the site quality feedback process and give management early "
                    "warning of quality problems.",
                ),
            ),
            (
                "5. Records",
                (
                    "Deviation forms, investigation reports, disposition records and complaint cross-references "
                    "are retained for the life of the product plus one year.",
                ),
            ),
            (
                "6. References",
                ("SOP-QA-031 Complaint Handling; SOP-QA-022 Corrective and Preventive Action; SOP-QA-004 Change Control.",),
            ),
        ),
    ),
    DemoDocument(
        filename="DEV-2026-0417_Stability_Chamber_Temperature_Excursion.docx",
        document_type="deviation",
        process_area="deviation_handling",
        title_block=(
            "DEV-2026-0417 Stability chamber SC-04 temperature excursion",
            "Raised 2026-03-04 | Owner: Stability QA | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "1. Description",
                (
                    "On 2026-03-04 at 02:15 the environmental monitoring system alarmed for stability chamber "
                    "SC-04 (25 C / 60% RH) after the temperature reached 29.1 C and stayed above the 27 C alert "
                    "limit for 6 hours 40 minutes.",
                    "Identification of nonconforming product: lots 24-118, 24-121 and 24-133 of Compound X "
                    "tablets were identified from the chamber inventory. Segregation of nonconforming product: "
                    "the affected samples were moved to quarantine cage QC-2 and tagged. Disposition of "
                    "nonconforming product is pending completion of the impact assessment.",
                    "This event was handled under SOP-QA-014, the procedure to define the controls for the "
                    "control of nonconforming product at this site.",
                    "Product complaint check: no entries in the complaint file relate to these lots, and the "
                    "complaint handling procedure was not triggered.",
                    "The excursion data were also entered into the quality feedback process for trending.",
                ),
            ),
            (
                "2. Investigation",
                (
                    "An investigation was conducted by Stability QA with Facilities Engineering. QA notified the "
                    "responsible department head (Stability Manager) within 24 hours of the alarm.",
                    "The need for the investigation and its rationale are documented in this section: any "
                    "excursion beyond the alert limit for more than four hours requires a formal impact "
                    "assessment.",
                    "This event was assessed as not serious and unexpected under the complaint handling "
                    "procedure, and the investigation and its findings are summarised here.",
                    "Disposition options considered were action to eliminate the nonconformity by re-testing at "
                    "the next scheduled pull, authorizing use under concession, and action to preclude original "
                    "intended use. Re-testing was selected; concession and destruction were not required.",
                    "The excursion was thoroughly investigated, including all lots stored in SC-04 during the "
                    "event window. Conclusions and followup actions are recorded in Section 5, and conclusions "
                    "and follow-up dates are tracked in the quality system.",
                ),
            ),
            (
                "3. Root Cause",
                (
                    "The compressor contactor on SC-04 failed to re-engage after a brief power dip, allowing the "
                    "chamber to warm. The failure was traced to a worn contactor beyond its service life.",
                ),
            ),
            (
                "4. Corrective Action (CAPA)",
                (
                    "The contactor was replaced on 2026-03-04 and the chamber was requalified with a 24-hour "
                    "temperature mapping run. Facilities added the contactor to the preventive maintenance "
                    "program with a 12-month replacement interval.",
                ),
            ),
            (
                "5. Closure",
                (
                    "Impact assessment concluded that the 6 hour 40 minute excursion has no impact on the "
                    "validity of stability data for the three lots. No advisory notice is required. Quality "
                    "Assurance approved closure on 2026-03-18.",
                ),
            ),
        ),
    ),
    DemoDocument(
        filename="DEV-2026-0433_Label_Reconciliation_Discrepancy.docx",
        document_type="deviation",
        process_area="deviation_handling",
        title_block=(
            "DEV-2026-0433 Label reconciliation discrepancy, packaging line 2",
            "Raised 2026-04-09 | Owner: Packaging | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "1. Description",
                (
                    "During packaging of lot 26-044 on 2026-04-09 the line operator could not reconcile 12 "
                    "printed labels: 1,012 labels were issued and 1,000 were applied, with no rejects returned. "
                    "Product was placed in quarantine pending disposition of nonconforming product.",
                    "The complaint file was checked and contains no related entries.",
                ),
            ),
            (
                "2. Investigation",
                (
                    "The operator recounted the labels and the count did not change. The supervisor believes the "
                    "missing labels were discarded by mistake.",
                ),
            ),
            ("3. Root Cause", ("Operator error.",)),
            ("4. Corrective Action (CAPA)", ("Operator was retrained on label handling.",)),
            ("5. Closure", ("Closed by the packaging supervisor on 2026-04-10.",)),
        ),
    ),
    DemoDocument(
        filename="SOP-QA-021_Corrective_and_Preventive_Action.docx",
        document_type="sop",
        process_area="capa",
        title_block=(
            "SOP-QA-021 Corrective and Preventive Action",
            "Version 2.1 | Effective 2026-02-01 | Owner: Quality Assurance | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "1. Purpose",
                (
                    "This SOP establishes the corrective and preventive action procedure for the site and "
                    "describes each step of the corrective and preventive action process, from initiation "
                    "through effectiveness review and closure.",
                ),
            ),
            (
                "2. Scope",
                (
                    "This SOP applies to corrective and preventive actions arising from deviations, audit "
                    "findings, complaints and trend reviews at all site functions.",
                ),
            ),
            (
                "3. Responsibilities",
                (
                    "The CAPA owner is responsible for the root cause investigation and for completing assigned "
                    "actions by the due date.",
                    "Quality Assurance approves each CAPA plan, verifies completion and approves closure.",
                ),
            ),
            (
                "4. Procedure",
                (
                    "For each CAPA the owner shall document how the team investigated the cause of the problem, "
                    "using tools such as 5-Why or fishbone analysis.",
                    "Determination of causes shall be recorded, and the corrective action to eliminate each "
                    "cause shall be defined with an owner and a due date.",
                    "Preventive action shall be raised for potential nonconformities identified through "
                    "trending of deviations, complaints and audit findings.",
                    "Any deviation shall be recorded and justified against the approved production and process "
                    "controls, and changes to those controls follow SOP-QA-004.",
                    "Quality Assurance shall verify the corrective action was implemented as planned before the "
                    "effectiveness check begins.",
                    "The effectiveness of the corrective action shall be reviewed 90 days after implementation. "
                    "The review of the effectiveness shall be documented with objective evidence that the "
                    "problem has not recurred.",
                    "CAPA metrics are submitted for management review each quarter, and outcomes are "
                    "disseminated to those directly responsible for the affected process.",
                ),
            ),
            (
                "5. Records",
                (
                    "CAPA plans, effectiveness checks and closure approvals are retained in the quality system "
                    "for the life of the product plus one year.",
                ),
            ),
            ("6. References", ("SOP-QA-014 Control of Nonconforming Product; SOP-QA-004 Change Control.",)),
        ),
    ),
    DemoDocument(
        filename="DEV-2026-0451_Filling_Line_Stopper_Feed_Jams.docx",
        document_type="deviation",
        process_area="capa",
        title_block=(
            "DEV-2026-0451 Filling line 3 stopper feed jams",
            "Raised 2026-05-12 | Owner: Sterile Manufacturing | Site: Acme Pharma Devices",
            SYNTHETIC_NOTICE,
        ),
        sections=(
            (
                "1. Description",
                (
                    "On 2026-05-12 filling line 3 stopped nine times during lot 26-071 because rubber stoppers "
                    "jammed in the feed bowl. Approximately 4% of filled vials were held for visual inspection. "
                    "Operations raised this deviation record on the same shift.",
                ),
            ),
            (
                "2. Investigation",
                (
                    "Quality Assurance reviewed the line clearance records, maintenance logs and stopper supplier "
                    "certificates. A root cause investigation was performed by a cross-functional team of "
                    "Manufacturing, Engineering and QA, which investigated the cause using a fishbone analysis "
                    "and a 5-Why review.",
                ),
            ),
            (
                "3. Root Cause",
                (
                    "The feed bowl vibration amplitude had drifted outside its qualified range after a spare "
                    "motor was fitted without recalibration. Determination of causes also identified that the "
                    "preventive maintenance checklist did not include an amplitude check.",
                ),
            ),
            (
                "4. Corrective Action (CAPA)",
                (
                    "CAPA-2026-0091 was opened under the site corrective and preventive action process. Planned "
                    "actions are to recalibrate the feed bowl, add an amplitude check to the maintenance "
                    "checklist and retrain the maintenance technicians; all actions are due by 2026-06-30. The "
                    "deviation was documented and approved by the QA manager on 2026-05-13.",
                ),
            ),
            (
                "5. Closure",
                (
                    "Results were presented at the monthly quality management review. Findings were "
                    "communicated to the personnel responsible for line 3 and to the maintenance team.",
                ),
            ),
        ),
    ),
)

_FIXED_TIMESTAMP = datetime(2026, 1, 1)


def build_document(demo: DemoDocument, output_dir: Path) -> Path:
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
    return [build_document(demo, output_dir) for demo in DEMO_DOCUMENTS]


if __name__ == "__main__":
    for written in build_all():
        print(f"Wrote {written}")
