import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register() -> str:
    response = client.post(
        "/auth/register",
        json={
            "org_name": "Onboarding Test Org",
            "industry": "device",
            "email": f"onboarding-{uuid.uuid4().hex}@acme.example.com",
            "password": "testpass123",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_list_scope_templates_returns_both_categories():
    response = client.get("/onboarding/scope-templates")
    assert response.status_code == 200
    categories = {t["scope_category"] for t in response.json()}
    assert categories == {"device_class_ii_diagnostic", "drug_otc_oral_liquid"}


def test_device_scope_template_detail_has_expected_shape():
    response = client.get("/onboarding/scope-templates/device_class_ii_diagnostic")
    assert response.status_code == 200
    body = response.json()
    assert body["industry"] == "device"
    assert body["source_note"]

    departments = {item["department"] for item in body["checklist_items"]}
    assert departments == {"qc", "qa", "utilities", "manufacturing", "engineering"}
    assert len(body["checklist_items"]) == 15

    categories = {std["vendor_category"] for std in body["vendor_standards"]}
    assert categories == {
        "raw_material_supplier",
        "contract_manufacturer",
        "calibration_test_service",
        "sterilization_service",
        "packaging_component_supplier",
    }
    assert len(body["vendor_standards"]) == 10


def test_drug_scope_template_detail_has_expected_shape():
    response = client.get("/onboarding/scope-templates/drug_otc_oral_liquid")
    assert response.status_code == 200
    body = response.json()
    assert body["industry"] == "drug"
    assert len(body["checklist_items"]) == 15
    assert len(body["vendor_standards"]) == 10


def test_unknown_scope_template_returns_404():
    response = client.get("/onboarding/scope-templates/not-a-real-category")
    assert response.status_code == 404


def test_checklist_items_have_match_phrases():
    response = client.get("/onboarding/scope-templates/device_class_ii_diagnostic")
    body = response.json()
    assert all(item["match_phrases"] for item in body["checklist_items"])
    assert all(std["match_phrases"] for std in body["vendor_standards"])


def test_adopt_scope_template_creates_org_scoped_checklist_items():
    token = _register()
    headers = _headers(token)

    response = client.post("/onboarding/scope-templates/device_class_ii_diagnostic/adopt", headers=headers)
    assert response.status_code == 200
    # 5 of the device template's 15 items share a (department, item_name)
    # with the global library (Equipment Calibration Records, CAPA Log,
    # Device History Record, Design History File, Risk Management File) —
    # those are intentionally skipped so adopting doesn't create a custom
    # item sitting right next to the global item it restates.
    assert response.json() == {"added": 10, "skipped": 5}

    checklist = client.get("/audit-simulation/checklist", headers=headers).json()
    custom_items = [item for item in checklist if item["is_custom"]]
    assert len(custom_items) == 10
    assert all(item["match_phrases"] for item in custom_items)

    # Re-adopting is idempotent: nothing new added, everything skipped.
    response = client.post("/onboarding/scope-templates/device_class_ii_diagnostic/adopt", headers=headers)
    assert response.json() == {"added": 0, "skipped": 15}


def test_adopt_unknown_scope_template_returns_404():
    token = _register()
    response = client.post("/onboarding/scope-templates/not-a-real-category/adopt", headers=_headers(token))
    assert response.status_code == 404
