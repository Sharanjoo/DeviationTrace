import uuid

from app.core.matching.rule_based import RuleBasedMatchingEngine
from app.models.document import Document
from app.models.document_section import DocumentSection
from app.models.regulatory_clause import RegulatoryClause

engine = RuleBasedMatchingEngine()


def _document(**kwargs) -> Document:
    return Document(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        type=kwargs.get("type", "sop"),
        title="test.docx",
        process_area=kwargs.get("process_area", "capa"),
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


def _clause(**kwargs) -> RegulatoryClause:
    return RegulatoryClause(
        id=uuid.uuid4(),
        regulation=kwargs.get("regulation", "qmsr"),
        clause_number=kwargs.get("clause_number", "8.5.2(e)"),
        requirement_text="Verify or validate corrective action effectiveness.",
        process_area=kwargs.get("process_area", "capa"),
        document_type_applicability=["sop", "deviation"],
        version=1,
        match_phrases=kwargs.get("match_phrases", ["verify the corrective action", "validate the corrective action"]),
        expected_heading=kwargs.get("expected_heading", "Corrective Action (CAPA)"),
    )


def test_fully_addressed_clause_produces_no_finding():
    document = _document()
    sections = [_section("Corrective Action (CAPA)", "We verify the corrective action and validate the corrective action annually.")]
    clause = _clause()

    findings = engine.evaluate(document, sections, [clause])

    assert findings == []


def test_zero_phrases_found_is_missing_critical():
    document = _document()
    sections = [_section("Procedure", "We assemble widgets according to spec.")]
    clause = _clause()

    findings = engine.evaluate(document, sections, [clause])

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "missing"
    assert finding.severity == "critical"
    assert finding.clause_id == clause.id
    # expected_heading section doesn't exist -> falls back to the only section
    assert finding.section_id == sections[0].id


def test_partial_phrase_coverage_is_partial_major():
    document = _document()
    sections = [_section("Corrective Action (CAPA)", "We verify the corrective action every quarter.")]
    clause = _clause()

    findings = engine.evaluate(document, sections, [clause])

    assert len(findings) == 1
    assert findings[0].status == "partial"
    assert findings[0].severity == "major"


def test_expected_heading_is_preferred_over_fallback():
    document = _document()
    sections = [
        _section("Unclassified", "cover page notes"),
        _section("Procedure", "generic body text"),
        _section("Corrective Action (CAPA)", "capa specific text with no match"),
    ]
    clause = _clause()

    findings = engine.evaluate(document, sections, [clause])

    assert findings[0].section_id == sections[2].id


def test_falls_back_to_unclassified_when_expected_heading_missing():
    document = _document()
    sections = [
        _section("Unclassified", "cover page notes"),
        _section("Procedure", "generic body text"),
    ]
    clause = _clause()

    findings = engine.evaluate(document, sections, [clause])

    assert findings[0].section_id == sections[0].id


def test_no_match_phrases_on_clause_is_skipped():
    document = _document()
    sections = [_section("Procedure", "anything")]
    clause = _clause(match_phrases=[])

    findings = engine.evaluate(document, sections, [clause])

    assert findings == []
