"""Idempotent loader for the vendor-audit standards library.

Reads backend/app/seed/data/vendor_standards/*.yaml and upserts rows keyed on
(vendor_category, requirement_name, version) so re-running after editing a
YAML file updates existing rows instead of duplicating them.

Run with: python -m app.seed.load_vendor_standards
"""

from pathlib import Path

import yaml

from app.database import SessionLocal
from app.models.vendor_standard import VendorStandard

DATA_DIR = Path(__file__).parent / "data" / "vendor_standards"


def load_vendor_standards() -> None:
    db = SessionLocal()
    try:
        loaded = 0
        for yaml_path in sorted(DATA_DIR.glob("*.yaml")):
            payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            vendor_category = payload["vendor_category"]
            for entry in payload["standards"]:
                version = entry.get("version", 1)
                existing = (
                    db.query(VendorStandard)
                    .filter(
                        VendorStandard.vendor_category == vendor_category,
                        VendorStandard.requirement_name == entry["requirement_name"],
                        VendorStandard.version == version,
                    )
                    .first()
                )
                fields = {
                    "citation": entry["citation"],
                    "requirement_text": entry["requirement_text"].strip(),
                    "match_phrases": entry.get("match_phrases", []),
                    "expected_heading": entry.get("expected_heading"),
                }
                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                else:
                    db.add(
                        VendorStandard(
                            vendor_category=vendor_category,
                            requirement_name=entry["requirement_name"],
                            version=version,
                            **fields,
                        )
                    )
                loaded += 1
        db.commit()
        print(f"Loaded/updated {loaded} vendor standards from {DATA_DIR}")
    finally:
        db.close()


if __name__ == "__main__":
    load_vendor_standards()
