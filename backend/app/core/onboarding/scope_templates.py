"""In-memory scope template library for new-company onboarding.

Reads backend/app/seed/data/scope_templates/*.yaml at import time. Unlike
the checklist/vendor-standards libraries, these aren't persisted to
Postgres — nothing references a scope template by foreign key, so a DB
table is unnecessary surface area for a read-only reference lookup.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parents[2] / "seed" / "data" / "scope_templates"


@dataclass(frozen=True)
class ChecklistItemTemplate:
    department: str
    item_name: str
    citation: str
    requirement_text: str
    match_phrases: tuple[str, ...]


@dataclass(frozen=True)
class VendorStandardTemplate:
    vendor_category: str
    requirement_name: str
    citation: str
    requirement_text: str
    match_phrases: tuple[str, ...]


@dataclass(frozen=True)
class ScopeTemplate:
    scope_category: str
    industry: str
    label: str
    description: str
    source_note: str
    checklist_items: tuple[ChecklistItemTemplate, ...]
    vendor_standards: tuple[VendorStandardTemplate, ...]


def _load_all() -> dict[str, ScopeTemplate]:
    templates: dict[str, ScopeTemplate] = {}
    for yaml_path in sorted(DATA_DIR.glob("*.yaml")):
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        template = ScopeTemplate(
            scope_category=payload["scope_category"],
            industry=payload["industry"],
            label=payload["label"],
            description=payload["description"].strip(),
            source_note=payload["source_note"].strip(),
            checklist_items=tuple(
                ChecklistItemTemplate(
                    department=item["department"],
                    item_name=item["item_name"],
                    citation=item["citation"],
                    requirement_text=item["requirement_text"].strip(),
                    match_phrases=tuple(item.get("match_phrases", [])),
                )
                for item in payload["checklist_items"]
            ),
            vendor_standards=tuple(
                VendorStandardTemplate(
                    vendor_category=std["vendor_category"],
                    requirement_name=std["requirement_name"],
                    citation=std["citation"],
                    requirement_text=std["requirement_text"].strip(),
                    match_phrases=tuple(std.get("match_phrases", [])),
                )
                for std in payload["vendor_standards"]
            ),
        )
        templates[template.scope_category] = template
    return templates


SCOPE_TEMPLATES: dict[str, ScopeTemplate] = _load_all()
