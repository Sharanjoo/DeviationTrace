import uuid

from app.core.vendor_audit.rule_based import RuleBasedVendorAuditEngine
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.vendor_standard import VendorStandard

engine = RuleBasedVendorAuditEngine()


def _document(**kwargs) -> Document:
    return Document(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        type="vendor_audit_report",
        title="test.docx",
        process_area="general",
        vendor_category=kwargs.get("vendor_category", "raw_material_supplier"),
        file_ref="unused",
        status="processing",
    )


def _section(heading: str, text: str) -> DocumentSection:
    return DocumentSection(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        heading=heading,
        text=text,
        order=0,
        span_start=0,
        span_end=len(text),
    )


def _standard(**kwargs) -> VendorStandard:
    return VendorStandard(
        id=uuid.uuid4(),
        vendor_category=kwargs.get("vendor_category", "raw_material_supplier"),
        requirement_name=kwargs.get("requirement_name", "Certificate of Analysis per lot"),
        citation="21 CFR 211.84(d)",
        requirement_text="A certificate of analysis shall be issued for each lot.",
        version=1,
        match_phrases=kwargs.get("match_phrases", ["certificate of analysis", "lot-specific test results"]),
        expected_heading=kwargs.get("expected_heading", "Certificate of Analysis"),
    )


def test_full_coverage_produces_satisfied_with_a_row():
    document = _document()
    sections = [
        _section(
            "Certificate of Analysis",
            "A certificate of analysis was issued, including lot-specific test results for every lot.",
        )
    ]
    standard = _standard()

    findings = engine.evaluate(document, sections, [standard])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "satisfied"
    assert finding.severity == "resolved"
    assert finding.standard_id == standard.id
    assert finding.section_id == sections[0].id


def test_zero_phrases_found_is_missing_critical():
    document = _document()
    sections = [_section("Procedure", "The vendor ships material on schedule.")]
    standard = _standard()

    findings = engine.evaluate(document, sections, [standard])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "missing"
    assert finding.severity == "critical"
    # expected_heading section doesn't exist -> falls back to the only section
    assert finding.section_id == sections[0].id


def test_partial_phrase_coverage_is_partial_major():
    document = _document()
    sections = [_section("Certificate of Analysis", "A certificate of analysis was issued for this shipment.")]
    standard = _standard()

    findings = engine.evaluate(document, sections, [standard])

    assert len(findings) == 1
    assert findings[0].status == "partial"
    assert findings[0].severity == "major"


def test_expected_heading_is_preferred_over_fallback():
    document = _document()
    sections = [
        _section("Unclassified", "cover page notes"),
        _section("Procedure", "generic body text"),
        _section("Certificate of Analysis", "certificate of analysis with no match on the second phrase"),
    ]
    standard = _standard()

    findings = engine.evaluate(document, sections, [standard])

    assert findings[0].section_id == sections[2].id


def test_falls_back_to_unclassified_when_expected_heading_missing():
    document = _document()
    sections = [
        _section("Unclassified", "cover page notes"),
        _section("Procedure", "generic body text"),
    ]
    standard = _standard()

    findings = engine.evaluate(document, sections, [standard])

    assert findings[0].section_id == sections[0].id


def test_no_match_phrases_on_standard_is_skipped():
    document = _document()
    sections = [_section("Procedure", "anything")]
    standard = _standard(match_phrases=[])

    findings = engine.evaluate(document, sections, [standard])

    assert findings == []
