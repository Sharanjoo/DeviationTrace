"""Idempotent loader for the global internal-audit checklist library.

Reads backend/app/seed/data/checklist/*.yaml and upserts rows keyed on
(department, item_name, version) so re-running after editing a YAML file
updates existing rows instead of duplicating them. Always filters to
org_id IS NULL (the global library) so this never matches or overwrites
an org's own custom checklist item that happens to share a department
and item_name — see AuditChecklistItem's org_id docstring.

Run with: python -m app.seed.load_checklist
"""

from pathlib import Path

import yaml

from app.database import SessionLocal
from app.models.audit_checklist_item import AuditChecklistItem

DATA_DIR = Path(__file__).parent / "data" / "checklist"


def load_checklist() -> None:
    db = SessionLocal()
    try:
        loaded = 0
        for yaml_path in sorted(DATA_DIR.glob("*.yaml")):
            payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            department = payload["department"]
            for entry in payload["items"]:
                version = entry.get("version", 1)
                existing = (
                    db.query(AuditChecklistItem)
                    .filter(
                        AuditChecklistItem.org_id.is_(None),
                        AuditChecklistItem.department == department,
                        AuditChecklistItem.item_name == entry["item_name"],
                        AuditChecklistItem.version == version,
                    )
                    .first()
                )
                fields = {
                    "citation": entry["citation"],
                    "requirement_text": entry["requirement_text"].strip(),
                    "match_phrases": entry.get("match_phrases", []),
                }
                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                else:
                    db.add(
                        AuditChecklistItem(
                            department=department,
                            item_name=entry["item_name"],
                            version=version,
                            **fields,
                        )
                    )
                loaded += 1
        db.commit()
        print(f"Loaded/updated {loaded} checklist items from {DATA_DIR}")
    finally:
        db.close()


if __name__ == "__main__":
    load_checklist()
