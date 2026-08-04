"""
Tests end-to-end del flujo principal, en modo mock (sin credenciales reales,
sin negocios reales — todo generado localmente).
"""
import os

# Si ya hay un DATABASE_URL definido externamente (p.ej. para probar contra
# Postgres real en CI), se respeta. Si no, se usa SQLite local por defecto.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_prospectapp.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def _register_and_login():
    client.post("/api/auth/register", json={"email": "demo@test.com", "password": "test1234"})
    resp = client.post("/api/auth/login", data={"username": "demo@test.com", "password": "test1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login():
    headers = _register_and_login()
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "demo@test.com"


def test_full_prospecting_flow():
    headers = _register_and_login()

    profile_resp = client.post("/api/profiles", headers=headers, json={
        "name": "Webs para peluquerías",
        "service_offered": "Creación de páginas web",
        "value_proposition": "Webs sencillas y rápidas para negocios locales",
        "cities": ["Algeciras"],
        "niches": ["peluquería"],
    })
    assert profile_resp.status_code == 200
    profile_id = profile_resp.json()["id"]

    search_resp = client.post("/api/searches", headers=headers, json={
        "profile_id": profile_id, "city": "Algeciras", "niche": "peluquería", "max_results": 5,
    })
    assert search_resp.status_code == 200
    businesses = search_resp.json()
    assert len(businesses) > 0

    business_id = businesses[0]["id"]
    detail_resp = client.get(f"/api/businesses/{business_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "score" in detail
    assert "opportunities" in detail

    msg_resp = client.post("/api/messages/generate", headers=headers, json={
        "business_id": business_id, "profile_id": profile_id, "channel": "email",
    })
    assert msg_resp.status_code == 200
    assert "body" in msg_resp.json()

    stage_resp = client.patch(f"/api/businesses/{business_id}/stage", headers=headers,
                               json={"stage": "preparado_contactar"})
    assert stage_resp.status_code == 200

    export_resp = client.get("/api/export/csv", headers=headers)
    assert export_resp.status_code == 200


def test_deduplication_by_place_id():
    headers = _register_and_login()
    profile_resp = client.post("/api/profiles", headers=headers, json={"name": "Perfil dedupe"})
    profile_id = profile_resp.json()["id"]

    r1 = client.post("/api/searches", headers=headers,
                      json={"profile_id": profile_id, "city": "Cadiz", "niche": "restaurante", "max_results": 3})
    r2 = client.post("/api/searches", headers=headers,
                      json={"profile_id": profile_id, "city": "Cadiz", "niche": "restaurante", "max_results": 3})
    ids_1 = {b["id"] for b in r1.json()}
    ids_2 = {b["id"] for b in r2.json()}
    assert ids_1 == ids_2  # mismos place_id -> mismos negocios, sin duplicar
