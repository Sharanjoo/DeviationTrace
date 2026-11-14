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


def test_new_org_has_not_completed_onboarding():
    token = _register()
    response = client.get("/onboarding/status", headers=_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["completed"] is False
    assert body["onboarded_at"] is None
    assert body["scope_category"] is None
    assert body["org_name"] == "Onboarding Test Org"
    assert body["industry"] == "device"


def test_adopting_a_template_completes_onboarding_and_remembers_scope():
    token = _register()
    client.post("/onboarding/scope-templates/device_class_ii_diagnostic/adopt", headers=_headers(token))

    body = client.get("/onboarding/status", headers=_headers(token)).json()
    assert body["completed"] is True
    assert body["onboarded_at"] is not None
    assert body["scope_category"] == "device_class_ii_diagnostic"
    assert body["scope_label"]


def test_completing_with_standard_checklist_marks_onboarded_without_scope():
    token = _register()
    response = client.post("/onboarding/complete", headers=_headers(token))
    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert response.json()["scope_category"] is None

    # Remembered server-side: a fresh read (e.g. a later login) sees it too.
    body = client.get("/onboarding/status", headers=_headers(token)).json()
    assert body["completed"] is True
    assert body["scope_label"] is None


def test_onboarding_status_is_kept_on_later_login():
    email = f"onboarding-{uuid.uuid4().hex}@acme.example.com"
    client.post(
        "/auth/register",
        json={"org_name": "Relogin Org", "industry": "drug", "email": email, "password": "testpass123"},
    )
    first = client.post("/auth/login", json={"email": email, "password": "testpass123"}).json()["access_token"]
    client.post("/onboarding/scope-templates/drug_otc_oral_liquid/adopt", headers=_headers(first))

    second = client.post("/auth/login", json={"email": email, "password": "testpass123"}).json()["access_token"]
    body = client.get("/onboarding/status", headers=_headers(second)).json()
    assert body["completed"] is True
    assert body["scope_category"] == "drug_otc_oral_liquid"


def test_first_onboarding_time_is_kept_when_completing_again():
    token = _register()
    first = client.post("/onboarding/complete", headers=_headers(token)).json()["onboarded_at"]
    client.post("/onboarding/scope-templates/device_class_ii_diagnostic/adopt", headers=_headers(token))
    body = client.get("/onboarding/status", headers=_headers(token)).json()
    assert body["onboarded_at"] == first
    assert body["scope_category"] == "device_class_ii_diagnostic"


def test_onboarding_status_requires_auth():
    assert client.get("/onboarding/status").status_code in (401, 403)
