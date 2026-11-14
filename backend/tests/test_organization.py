"""Company profile, members and roles (admin / member / viewer)."""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register():
    email = f"owner-{uuid.uuid4().hex}@acme.example.com"
    response = client.post(
        "/auth/register",
        json={"org_name": "Roles Org", "industry": "device", "email": email, "password": "testpass123", "full_name": "Olive Owner"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _add(admin, role="member"):
    email = f"m-{uuid.uuid4().hex}@acme.example.com"
    response = client.post("/org/members", headers=admin, json={"full_name": "Mia Member", "email": email, "role": role})
    assert response.status_code == 201, response.text
    body = response.json()
    login = client.post("/auth/login", json={"email": email, "password": body["temporary_password"]})
    assert login.status_code == 200
    return body["member"], {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_registering_makes_you_the_admin():
    admin = _register()
    profile = client.get("/org/profile", headers=admin).json()
    assert profile["you"]["role"] == "admin" and profile["you"]["full_name"] == "Olive Owner"
    assert profile["member_count"] == 1


def test_admin_adds_member_who_can_sign_in_with_temporary_password():
    admin = _register()
    member, member_headers = _add(admin)
    assert member["role"] == "member"
    you = client.get("/org/profile", headers=member_headers).json()["you"]
    assert you["id"] == member["id"]
    names = [m["full_name"] for m in client.get("/org/members", headers=admin).json()]
    assert names == ["Olive Owner", "Mia Member"]


def test_duplicate_email_and_bad_role_are_rejected():
    admin = _register()
    email = f"dup-{uuid.uuid4().hex}@acme.example.com"
    body = {"full_name": "A", "email": email}
    assert client.post("/org/members", headers=admin, json=body).status_code == 201
    assert client.post("/org/members", headers=admin, json=body).status_code == 409
    assert client.post("/org/members", headers=admin, json={**body, "email": "x" + email, "role": "owner"}).status_code == 422


def test_only_admins_manage_members_and_profile():
    admin = _register()
    member, member_headers = _add(admin)
    assert client.post("/org/members", headers=member_headers, json={"full_name": "X", "email": "x@acme.example.com"}).status_code == 403
    assert client.patch("/org/profile", headers=member_headers, json={"name": "Hijacked"}).status_code == 403
    assert client.patch(f"/org/members/{member['id']}", headers=member_headers, json={"role": "admin"}).status_code == 403
    # ...but can rename themselves.
    renamed = client.patch(f"/org/members/{member['id']}", headers=member_headers, json={"full_name": "Mia M."})
    assert renamed.status_code == 200 and renamed.json()["full_name"] == "Mia M."


def test_viewer_can_read_but_not_change_anything():
    admin = _register()
    _, viewer = _add(admin, role="viewer")
    assert client.get("/audit-simulation/checklist", headers=viewer).status_code == 200
    assert client.get("/vendors", headers=viewer).status_code == 200
    refused = client.post("/audit-simulation/run", headers=viewer)
    assert refused.status_code == 403 and "view-only" in refused.json()["detail"]
    assert client.post("/vendors", headers=viewer, json={"name": "V", "vendor_category": "raw_material_supplier"}).status_code == 403


def test_role_changes_apply_immediately():
    admin = _register()
    member, member_headers = _add(admin)
    client.patch(f"/org/members/{member['id']}", headers=admin, json={"role": "viewer"})
    assert client.post("/audit-simulation/run", headers=member_headers).status_code == 403
    client.patch(f"/org/members/{member['id']}", headers=admin, json={"role": "member"})
    assert client.post("/audit-simulation/run", headers=member_headers).status_code == 200


def test_removed_member_loses_access_and_cannot_log_in():
    admin = _register()
    email = f"gone-{uuid.uuid4().hex}@acme.example.com"
    created = client.post("/org/members", headers=admin, json={"full_name": "Gone", "email": email}).json()
    token = client.post("/auth/login", json={"email": email, "password": created["temporary_password"]}).json()["access_token"]

    assert client.delete(f"/org/members/{created['member']['id']}", headers=admin).status_code == 204
    assert client.get("/org/profile", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": created["temporary_password"]}).status_code == 401
    assert all(m["id"] != created["member"]["id"] for m in client.get("/org/members", headers=admin).json())


def test_organization_always_keeps_an_admin():
    admin = _register()
    me = client.get("/org/profile", headers=admin).json()["you"]
    assert client.delete(f"/org/members/{me['id']}", headers=admin).status_code == 409
    assert client.patch(f"/org/members/{me['id']}", headers=admin, json={"role": "member"}).status_code == 409

    second, _ = _add(admin, role="admin")
    # With another admin, stepping down is allowed.
    assert client.patch(f"/org/members/{me['id']}", headers=admin, json={"role": "member"}).status_code == 200
    assert client.get("/org/profile", headers=admin).json()["you"]["role"] == "member"


def test_admin_can_rename_company():
    admin = _register()
    assert client.patch("/org/profile", headers=admin, json={"name": "  Acme Devices  "}).json()["name"] == "Acme Devices"


def test_members_of_other_orgs_are_not_visible_or_editable():
    a, b = _register(), _register()
    member, _ = _add(a)
    assert all(m["id"] != member["id"] for m in client.get("/org/members", headers=b).json())
    assert client.patch(f"/org/members/{member['id']}", headers=b, json={"role": "viewer"}).status_code == 404
    assert client.delete(f"/org/members/{member['id']}", headers=b).status_code == 404
