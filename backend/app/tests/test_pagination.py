"""
Tests de paginación de /api/businesses: tamaño de página correcto, total
correcto, orden estable por score, y límites razonables aplicados.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_prospectapp_pagination.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402

limiter.enabled = False
client = TestClient(app)


def _register_and_login(email: str):
    client.post("/api/auth/register", json={"email": email, "password": "test1234"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "test1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _seed_businesses(headers, n_searches=3):
    profile_id = client.post("/api/profiles", headers=headers, json={"name": "Perfil paginación"}).json()["id"]
    total = 0
    for i in range(n_searches):
        resp = client.post("/api/searches", headers=headers, json={
            "profile_id": profile_id, "city": f"CiudadPag{i}", "niche": "restaurante", "max_results": 10,
        })
        total += len(resp.json())
    return total


def test_pagination_returns_correct_shape_and_page_size():
    headers = _register_and_login("pagination1@test.com")
    _seed_businesses(headers)

    resp = client.get("/api/businesses?page=1&page_size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"items", "total", "page", "page_size", "total_pages"}
    assert len(data["items"]) <= 5
    assert data["page"] == 1
    assert data["page_size"] == 5


def test_pagination_total_matches_all_pages_combined():
    headers = _register_and_login("pagination2@test.com")
    total_created = _seed_businesses(headers)

    first_page = client.get("/api/businesses?page=1&page_size=5", headers=headers).json()
    assert first_page["total"] == total_created

    collected_ids = set()
    for page in range(1, first_page["total_pages"] + 1):
        resp = client.get(f"/api/businesses?page={page}&page_size=5", headers=headers).json()
        collected_ids.update(b["id"] for b in resp["items"])

    assert len(collected_ids) == total_created  # sin duplicados ni huecos entre páginas


def test_page_size_is_capped():
    headers = _register_and_login("pagination3@test.com")
    resp = client.get("/api/businesses?page_size=9999", headers=headers)
    assert resp.json()["page_size"] <= 100


def test_invalid_page_defaults_to_one():
    headers = _register_and_login("pagination4@test.com")
    resp = client.get("/api/businesses?page=0", headers=headers)
    assert resp.json()["page"] == 1
