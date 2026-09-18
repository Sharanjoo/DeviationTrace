"""Idempotent loader for the regulatory clause library.

Reads backend/app/seed/data/*.yaml and upserts rows keyed on
(regulation, clause_number, version) so re-running after editing a YAML
file updates existing rows instead of duplicating them.

Run with: python -m app.seed.load_clauses
"""

from pathlib import Path

import yaml

from app.database import SessionLocal
from app.models.regulatory_clause import RegulatoryClause

DATA_DIR = Path(__file__).parent / "data"


def load_clauses() -> None:
    db = SessionLocal()
    try:
        loaded = 0
        for yaml_path in sorted(DATA_DIR.glob("*.yaml")):
            payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            regulation = payload["regulation"]
            for entry in payload["clauses"]:
                version = entry.get("version", 1)
                existing = (
                    db.query(RegulatoryClause)
                    .filter(
                        RegulatoryClause.regulation == regulation,
                        RegulatoryClause.clause_number == entry["clause_number"],
                        RegulatoryClause.version == version,
                    )
                    .first()
                )
                fields = {
                    "requirement_text": entry["requirement_text"].strip(),
                    "process_area": entry["process_area"],
                    "document_type_applicability": entry["document_type_applicability"],
                }
                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                else:
                    db.add(
                        RegulatoryClause(
                            regulation=regulation,
                            clause_number=entry["clause_number"],
                            version=version,
                            **fields,
                        )
                    )
                loaded += 1
        db.commit()
        print(f"Loaded/updated {loaded} clauses from {DATA_DIR}")
    finally:
        db.close()


if __name__ == "__main__":
    load_clauses()
