"""Requires a running Postgres with migrations applied and clauses seeded
(see README). Run: docker compose up -d && alembic upgrade head &&
python -m app.seed.load_clauses && pytest."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_clauses_returns_seeded_data() -> None:
    response = client.get("/clauses")
    assert response.status_code == 200
    clauses = response.json()
    assert len(clauses) > 0
    regulations = {c["regulation"] for c in clauses}
    assert regulations == {"qmsr", "iso13485", "cfr211"}


def test_filter_clauses_by_process_area() -> None:
    response = client.get("/clauses", params={"process_area": "capa"})
    assert response.status_code == 200
    clauses = response.json()
    assert all(c["process_area"] == "capa" for c in clauses)
    assert len(clauses) > 0
