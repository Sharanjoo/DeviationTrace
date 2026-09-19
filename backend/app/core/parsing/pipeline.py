from dataclasses import dataclass

from app.core.parsing.classify import detect_process_area
from app.core.parsing.extract import extract_text
from app.core.parsing.sections import SectionData, split_into_sections


@dataclass
class PipelineResult:
    sections: list[SectionData]
    detected_process_area: str | None
    detected_confidence: float


def run_pipeline(file_ref: str, document_type: str) -> PipelineResult:
    text = extract_text(file_ref)
    sections = split_into_sections(text, document_type)
    detected_process_area, confidence = detect_process_area(text)
    return PipelineResult(
        sections=sections,
        detected_process_area=detected_process_area,
        detected_confidence=confidence,
    )
