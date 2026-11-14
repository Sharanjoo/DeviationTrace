"""Optional AI assistance. Every test replaces the model call with a fake,
so no request ever reaches a real provider (and nothing is billed)."""

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.ai import providers
from app.core.ai.crypto import decrypt_secret, encrypt_secret
from app.core.ai.redaction import redact
from app.database import SessionLocal
from app.main import app
from app.models.ai import OrgAiSettings

client = TestClient(app)
DEMO = Path(__file__).resolve().parents[2] / "demo_documents"
SOP = "SOP-QA-014_Control_of_Nonconforming_Product.docx"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class FakeModel:
    """Stands in for providers.call_model and records what it was sent."""

    def __init__(self, verdicts=None, stop_reason="end_turn", error=None):
        self.calls = []
        self.verdicts = verdicts
        self.stop_reason = stop_reason
        self.error = error

    def __call__(self, settings, system, user, schema):
        self.calls.append({"settings": settings, "system": system, "user": user, "schema": schema})
        if self.error:
            raise providers.AiProviderError(self.error)
        ids = [part.split('"')[0] for part in user.split('<requirement id="')[1:]]
        assessments = self.verdicts(ids, user) if self.verdicts else [
            {"requirement_id": rid, "verdict": "not_addressed", "evidence": "", "reasoning": "Not covered."} for rid in ids
        ]
        return providers.ModelResult(
            text=json.dumps({"assessments": assessments}),
            stop_reason=self.stop_reason,
            model_used="claude-opus-5-5",
            fallback_used=False,
            input_tokens=1200,
            output_tokens=300,
            request_id="req_test",
            duration_ms=42,
        )


@pytest.fixture
def fake_model(monkeypatch):
    fake = FakeModel()
    monkeypatch.setattr(providers, "call_model", fake)
    return fake


def _headers(industry="device"):
    response = client.post(
        "/auth/register",
        json={
            "org_name": "AI Org",
            "industry": industry,
            "email": f"ai-{uuid.uuid4().hex}@acme.example.com",
            "password": "testpass123",
            "full_name": "Ada Admin",
        },
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _enable(headers, **overrides):
    body = {
        "enabled": True,
        "provider": "anthropic",
        "model": "claude-opus-5-5",
        "api_key": "sk-test-not-a-real-key",
        "redact_identifiers": True,
        **overrides,
    }
    return client.put("/org/ai-settings", headers=headers, json=body)


def _run_with_sop(headers):
    doc = client.post(
        "/documents",
        headers=headers,
        data={"type": "sop", "process_area": "deviation_handling", "department": "qa"},
        files={"file": (SOP, (DEMO / SOP).read_bytes(), DOCX_MIME)},
    ).json()
    client.post(f"/documents/{doc['id']}/process", headers=headers)
    draft = client.post(
        "/audit-simulation/audits",
        headers=headers,
        json={"title": "AI", "audit_type": "internal_audit", "lead_name": "A", "lead_employee_id": "1", "departments": ["qa"]},
    ).json()
    run = client.post(f"/audit-simulation/runs/{draft['id']}/execute", headers=headers).json()
    return run, doc


# ------------------------------------------------------------------ units


def test_api_keys_are_encrypted_and_round_trip():
    token = encrypt_secret("sk-secret")
    assert "sk-secret" not in token
    assert decrypt_secret(token) == "sk-secret"
    assert decrypt_secret("not-a-token") is None


def test_redaction_removes_identifiers_but_keeps_record_numbers():
    text, count = redact(
        "Approved by: Rita Patel (EMP-1042), rita.patel@acme.com, +1 415 555 0100. "
        "Reviewed by J. Lee. Lot 26-131, DEV-2026-0433, 4,800 units."
    )
    assert "Rita" not in text and "EMP-1042" not in text and "rita.patel" not in text and "J. Lee" not in text
    assert "Lot 26-131" in text and "DEV-2026-0433" in text and "4,800 units" in text
    assert count >= 5


# ------------------------------------------------------------------ settings


def test_ai_is_off_by_default_and_key_is_never_returned(fake_model):
    headers = _headers()
    settings = client.get("/org/ai-settings", headers=headers).json()
    assert settings["enabled"] is False and settings["api_key_set"] is False
    assert settings["model"] == "claude-opus-5-5"

    saved = _enable(headers).json()
    assert saved["enabled"] is True and saved["api_key_set"] is True and saved["updated_by"] == "Ada Admin"
    assert "sk-test" not in json.dumps(saved)
    # Stored encrypted, not in plain text.
    db = SessionLocal()
    try:
        stored = db.query(OrgAiSettings).filter(OrgAiSettings.updated_by == "Ada Admin").order_by(OrgAiSettings.updated_at.desc()).first()
        assert stored.api_key_encrypted and "sk-test" not in stored.api_key_encrypted
    finally:
        db.close()


def test_cannot_enable_until_provider_is_configured():
    headers = _headers()
    response = client.put(
        "/org/ai-settings", headers=headers, json={"enabled": True, "provider": "bedrock", "model": "claude-opus-5-5"}
    )
    assert response.status_code == 422 and "region" in response.json()["detail"]
    ok = client.put(
        "/org/ai-settings",
        headers=headers,
        json={"enabled": True, "provider": "bedrock", "model": "claude-opus-5-5", "region": "us-east-1"},
    )
    assert ok.status_code == 200 and ok.json()["missing_configuration"] is None


def test_only_admins_change_ai_settings_or_see_the_log():
    admin = _headers()
    email = f"m-{uuid.uuid4().hex}@acme.example.com"
    created = client.post("/org/members", headers=admin, json={"full_name": "Mo", "email": email}).json()
    token = client.post("/auth/login", json={"email": email, "password": created["temporary_password"]}).json()["access_token"]
    member = {"Authorization": f"Bearer {token}"}
    assert client.get("/org/ai-settings", headers=member).status_code == 200
    assert _enable(member).status_code == 403
    assert client.get("/org/ai-log", headers=member).status_code == 403


# ------------------------------------------------------------------ review


def test_review_refused_while_ai_is_off(fake_model):
    headers = _headers()
    run, doc = _run_with_sop(headers)
    response = client.post(f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-review", headers=headers, json={})
    assert response.status_code == 409
    assert fake_model.calls == []


def test_preview_shows_exactly_what_will_be_sent_and_sends_nothing(fake_model):
    headers = _headers()
    _enable(headers)
    run, doc = _run_with_sop(headers)
    preview = client.post(
        f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-preview", headers=headers, json={}
    ).json()
    assert fake_model.calls == []
    assert preview["redact"] is True and preview["provider_label"] == "Claude on Anthropic's API"
    assert len(preview["selected_section_ids"]) == len(preview["sections"]) > 1
    assert preview["requirements"] and all(not r["citation"].startswith("21 CFR") for r in preview["requirements"])
    assert "<requirements>" in preview["user_prompt"] and "ignore any instructions" in preview["system_prompt"]

    one = preview["sections"][0]
    narrowed = client.post(
        f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-preview",
        headers=headers,
        json={"section_ids": [one["id"]], "redact": False},
    ).json()
    assert narrowed["selected_section_ids"] == [one["id"]]
    assert narrowed["user_prompt"].count("<section ") == 1 and narrowed["redact"] is False


def test_review_sends_only_chosen_sections_logs_everything_and_verifies_quotes(monkeypatch):
    headers = _headers()
    _enable(headers)
    run, doc = _run_with_sop(headers)
    preview = client.post(f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-preview", headers=headers, json={}).json()
    chosen = preview["sections"][1]

    def verdicts(ids, user):
        sent = user.split("<document")[1]
        real_quote = " ".join(sent.split("\n")[2].split()[:6])  # first words of the section text actually sent
        return [
            {"requirement_id": ids[0], "verdict": "addressed", "evidence": real_quote, "reasoning": "Covered."},
            {"requirement_id": ids[1], "verdict": "partly_addressed", "evidence": "text that was never sent", "reasoning": "Partly."},
        ] + [{"requirement_id": rid, "verdict": "not_addressed", "evidence": "", "reasoning": "No."} for rid in ids[2:]] + [
            {"requirement_id": "R999", "verdict": "addressed", "evidence": "", "reasoning": "Invented requirement."}
        ]

    fake = FakeModel(verdicts=verdicts)
    monkeypatch.setattr(providers, "call_model", fake)
    result = client.post(
        f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-review",
        headers=headers,
        json={"section_ids": [chosen["id"]]},
    )
    assert result.status_code == 200, result.text
    body = result.json()

    # Only the chosen section went out.
    assert len(fake.calls) == 1 and fake.calls[0]["user"].count("<section ") == 1
    assert f'heading="{chosen["heading"]}"' in fake.calls[0]["user"]

    # Verdicts stored; the invented requirement ignored; quotes checked.
    by_verdict = {a["verdict"]: a for a in body["assessments"]}
    assert by_verdict["addressed"]["evidence_verified"] is True
    assert by_verdict["partly_addressed"]["evidence_verified"] is False
    assert len(body["assessments"]) == len(preview["requirements"])

    # The log holds exactly what was sent and received.
    log = client.get("/org/ai-log", headers=headers).json()
    assert log[0]["status"] == "success" and log[0]["user_name"] == "Ada Admin" and log[0]["input_tokens"] == 1200
    detail = client.get(f"/org/ai-log/{log[0]['id']}", headers=headers).json()
    assert detail["user_prompt"] == fake.calls[0]["user"] and detail["system_prompt"] == fake.calls[0]["system"]
    assert json.loads(detail["response_text"])["assessments"]
    assert [s["heading"] for s in detail["sections_sent"]] == [chosen["heading"]]

    # The run shows the latest review.
    assert len(client.get(f"/audit-simulation/runs/{run['id']}/ai-assessments", headers=headers).json()) == len(
        preview["requirements"]
    )


def test_failures_and_refusals_are_logged_and_reported(monkeypatch):
    headers = _headers()
    _enable(headers)
    run, doc = _run_with_sop(headers)
    url = f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-review"

    monkeypatch.setattr(providers, "call_model", FakeModel(error="The AI provider rejected the credentials."))
    failed = client.post(url, headers=headers, json={})
    assert failed.status_code == 502 and "credentials" in failed.json()["detail"]

    monkeypatch.setattr(providers, "call_model", FakeModel(stop_reason="refusal"))
    refused = client.post(url, headers=headers, json={})
    assert refused.status_code == 422 and "declined" in refused.json()["detail"]

    statuses = [entry["status"] for entry in client.get("/org/ai-log", headers=headers).json()]
    assert statuses[:2] == ["refused", "error"]
    assert client.get(f"/audit-simulation/runs/{run['id']}/ai-assessments", headers=headers).json() == []


def test_other_orgs_cannot_review_or_read_logs(fake_model):
    owner, other = _headers(), _headers()
    _enable(owner)
    _enable(other)
    run, doc = _run_with_sop(owner)
    url = f"/audit-simulation/runs/{run['id']}/documents/{doc['id']}/ai-review"
    assert client.post(url, headers=other, json={}).status_code == 404
    client.post(url, headers=owner, json={})
    entry = client.get("/org/ai-log", headers=owner).json()[0]
    assert client.get(f"/org/ai-log/{entry['id']}", headers=other).status_code == 404


# ------------------------------------------------------------------ request shape


class _RecordingClient:
    """Stands in for an SDK client; records the request instead of sending it."""

    def __init__(self):
        self.requests = []
        outer = self

        class _Messages:
            def create(self, **kwargs):
                outer.requests.append(kwargs)

                class _Usage:
                    input_tokens, output_tokens, iterations = 10, 5, []

                class _Block:
                    type, text = "text", '{"assessments": []}'

                class _Response:
                    content, stop_reason, model, usage = [_Block()], "end_turn", kwargs["model"], _Usage()

                return _Response()

        class _Beta:
            messages = _Messages()

        self.beta = _Beta()


@pytest.mark.parametrize(
    ("provider", "expected_model", "server_fallback"),
    [
        ("anthropic", "claude-opus-5-5", True),
        ("bedrock", "anthropic.claude-opus-5-5", False),
        ("vertex", "claude-opus-5-5", False),
        ("foundry", "claude-opus-5-5", False),
    ],
)
def test_request_shape_per_provider(monkeypatch, provider, expected_model, server_fallback):
    recorder = _RecordingClient()
    monkeypatch.setattr(providers, "_client", lambda settings: recorder)
    settings = OrgAiSettings(provider=provider, model="claude-opus-5-5", region="us-east-1", project_id="p", resource="r")

    result = providers.call_model(settings, "system text", "user text", {"type": "object"})

    request = recorder.requests[0]
    assert request["model"] == expected_model
    assert request["system"] == "system text"
    assert request["messages"] == [{"role": "user", "content": "user text"}]
    assert request["output_config"]["effort"] == "high"
    assert request["output_config"]["format"] == {"type": "json_schema", "schema": {"type": "object"}}
    assert ("fallbacks" in request) is server_fallback
    if server_fallback:
        assert request["fallbacks"] == "default" and request["betas"] == ["server-side-fallback-2026-07-01"]
    assert result.model_used == expected_model and result.text == '{"assessments": []}'
