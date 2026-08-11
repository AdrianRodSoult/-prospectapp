"""
Tests de equipos/organizaciones: cada registro nuevo crea una organización
personal automáticamente; invitar a un compañero comparte los datos entre
ambos; equipos distintos siguen completamente aislados entre sí.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_prospectapp_orgs.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402

limiter.enabled = False
client = TestClient(app)


def _register_and_login(email: str):
    client.post("/api/auth/register", json={"email": email, "password": "test1234"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "test1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_new_user_gets_personal_organization_as_owner():
    headers = _register_and_login("solo1@test.com")
    resp = client.get("/api/organizations/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["my_role"] == "owner"
    assert len(data["members"]) == 1
    assert data["members"][0]["status"] == "activo"


def test_invite_existing_user_shares_organization():
    headers_owner = _register_and_login("owner1@test.com")
    headers_teammate = _register_and_login("teammate1@test.com")

    resp = client.post("/api/organizations/invite", headers=headers_owner,
                        json={"email": "teammate1@test.com", "role": "member"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "activo"

    org_owner = client.get("/api/organizations/me", headers=headers_owner).json()
    org_teammate = client.get("/api/organizations/me", headers=headers_teammate).json()
    assert org_owner["id"] == org_teammate["id"]
    assert org_teammate["my_role"] == "member"


def test_invite_new_email_creates_pending_then_resolves_on_signup():
    headers_owner = _register_and_login("owner2@test.com")

    resp = client.post("/api/organizations/invite", headers=headers_owner,
                        json={"email": "notyetregistered@test.com", "role": "member"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "invitación pendiente"

    # Antes de registrarse, el invitado no existe como usuario todavía.
    org_before = client.get("/api/organizations/me", headers=headers_owner).json()
    pending = [m for m in org_before["members"] if m["email"] == "notyetregistered@test.com"]
    assert len(pending) == 1
    assert pending[0]["status"] == "invitación pendiente"

    # Al registrarse con ese email, se une automáticamente (no crea org propia).
    headers_invited = _register_and_login("notyetregistered@test.com")
    org_after_signup = client.get("/api/organizations/me", headers=headers_invited).json()
    assert org_after_signup["id"] == org_before["id"]
    assert org_after_signup["my_role"] == "member"


def test_member_without_invite_permission_cannot_invite():
    headers_owner = _register_and_login("owner3@test.com")
    headers_member = _register_and_login("member3@test.com")
    client.post("/api/organizations/invite", headers=headers_owner,
                json={"email": "member3@test.com", "role": "member"})

    resp = client.post("/api/organizations/invite", headers=headers_member,
                        json={"email": "otro@test.com", "role": "member"})
    assert resp.status_code == 403


def test_teammates_share_businesses_and_profiles():
    headers_owner = _register_and_login("team-owner@test.com")
    headers_mate = _register_and_login("team-mate@test.com")
    client.post("/api/organizations/invite", headers=headers_owner,
                json={"email": "team-mate@test.com", "role": "member"})

    profile_id = client.post("/api/profiles", headers=headers_owner, json={"name": "Perfil equipo"}).json()["id"]

    # El compañero ve el perfil creado por el dueño, sin haberlo creado él.
    profiles_seen_by_mate = client.get("/api/profiles", headers=headers_mate).json()
    assert any(p["id"] == profile_id for p in profiles_seen_by_mate)

    # El compañero puede buscar usando ese perfil compartido.
    search_resp = client.post("/api/searches", headers=headers_mate,
                               json={"profile_id": profile_id, "city": "Sevilla", "niche": "gimnasio", "max_results": 3})
    assert search_resp.status_code == 200
    business_ids = [b["id"] for b in search_resp.json()]
    assert len(business_ids) > 0

    # El dueño original ve esos mismos negocios en su propio listado.
    owner_list = client.get("/api/businesses", headers=headers_owner).json()
    owner_ids = {b["id"] for b in owner_list["items"]}
    assert set(business_ids).issubset(owner_ids)


def test_different_organizations_remain_fully_isolated():
    headers_team_a = _register_and_login("isoteam-a@test.com")
    headers_team_b = _register_and_login("isoteam-b@test.com")

    profile_a = client.post("/api/profiles", headers=headers_team_a, json={"name": "Perfil A"}).json()["id"]
    profile_b = client.post("/api/profiles", headers=headers_team_b, json={"name": "Perfil B"}).json()["id"]

    biz_a = client.post("/api/searches", headers=headers_team_a,
                         json={"profile_id": profile_a, "city": "Bilbao", "niche": "dentista", "max_results": 3}).json()
    biz_b_ids = {b["id"] for b in client.post("/api/searches", headers=headers_team_b,
                 json={"profile_id": profile_b, "city": "Bilbao", "niche": "dentista", "max_results": 3}).json()}

    target_id = biz_a[0]["id"]
    assert target_id not in biz_b_ids  # equipos distintos, sin compartir aunque busquen lo mismo

    resp = client.get(f"/api/businesses/{target_id}", headers=headers_team_b)
    assert resp.status_code == 404

    resp = client.get("/api/profiles", headers=headers_team_b).json()
    assert profile_a not in [p["id"] for p in resp]
