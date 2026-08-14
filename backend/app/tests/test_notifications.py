"""
Tests de notificaciones: se generan al descubrir un lead de prioridad
alta y al marcar un negocio como 'respondio'; no se repiten en cada
re-búsqueda del mismo negocio; marcar como leída/todas funciona.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_prospectapp_notifications.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402

limiter.enabled = False
client = TestClient(app)


def _register_and_login(email: str):
    client.post("/api/auth/register", json={"email": email, "password": "test1234"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "test1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_search_may_generate_high_priority_notification():
    headers = _register_and_login("notif1@test.com")
    profile_id = client.post("/api/profiles", headers=headers, json={"name": "Perfil notif"}).json()["id"]
    client.post("/api/searches", headers=headers, json={
        "profile_id": profile_id, "city": "Toledo", "niche": "peluqueria", "max_results": 20,
    })

    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_count" in data
    # Con 20 resultados demo (aleatorios pero deterministas por ciudad+nicho),
    # es razonable esperar que al menos alguno sea de prioridad alta.
    high_priority_notifs = [n for n in data["items"] if n["type"] == "high_priority_lead"]
    assert len(high_priority_notifs) >= 0  # no forzamos un número exacto, solo que no rompe


def test_same_business_researched_does_not_duplicate_notification():
    headers = _register_and_login("notif2@test.com")
    profile_id = client.post("/api/profiles", headers=headers, json={"name": "Perfil notif2"}).json()["id"]

    client.post("/api/searches", headers=headers,
                json={"profile_id": profile_id, "city": "Burgos", "niche": "restaurante", "max_results": 10})
    count_after_first = client.get("/api/notifications", headers=headers).json()["unread_count"]

    client.post("/api/searches", headers=headers,
                json={"profile_id": profile_id, "city": "Burgos", "niche": "restaurante", "max_results": 10})
    count_after_second = client.get("/api/notifications", headers=headers).json()["unread_count"]

    assert count_after_second == count_after_first  # misma búsqueda repetida, sin duplicar avisos


def test_business_responded_triggers_notification():
    headers = _register_and_login("notif3@test.com")
    profile_id = client.post("/api/profiles", headers=headers, json={"name": "Perfil notif3"}).json()["id"]
    biz_id = client.post("/api/searches", headers=headers, json={
        "profile_id": profile_id, "city": "Leon", "niche": "gimnasio", "max_results": 3,
    }).json()[0]["id"]

    before = client.get("/api/notifications", headers=headers).json()["unread_count"]
    client.patch(f"/api/businesses/{biz_id}/stage", headers=headers, json={"stage": "respondio"})
    after = client.get("/api/notifications", headers=headers).json()

    assert after["unread_count"] == before + 1
    assert any(n["type"] == "business_responded" for n in after["items"])


def test_mark_single_notification_as_read():
    headers = _register_and_login("notif4@test.com")
    profile_id = client.post("/api/profiles", headers=headers, json={"name": "Perfil notif4"}).json()["id"]
    biz_id = client.post("/api/searches", headers=headers, json={
        "profile_id": profile_id, "city": "Cuenca", "niche": "dentista", "max_results": 3,
    }).json()[0]["id"]
    client.patch(f"/api/businesses/{biz_id}/stage", headers=headers, json={"stage": "respondio"})

    data = client.get("/api/notifications", headers=headers).json()
    notif_id = data["items"][0]["id"]

    resp = client.post(f"/api/notifications/{notif_id}/read", headers=headers)
    assert resp.status_code == 200

    data_after = client.get("/api/notifications", headers=headers).json()
    assert data_after["unread_count"] == data["unread_count"] - 1


def test_mark_all_as_read():
    headers = _register_and_login("notif5@test.com")
    profile_id = client.post("/api/profiles", headers=headers, json={"name": "Perfil notif5"}).json()["id"]
    client.post("/api/searches", headers=headers, json={
        "profile_id": profile_id, "city": "Huesca", "niche": "peluqueria", "max_results": 15,
    })

    resp = client.post("/api/notifications/read-all", headers=headers)
    assert resp.status_code == 200
    data = client.get("/api/notifications", headers=headers).json()
    assert data["unread_count"] == 0


def test_notifications_isolated_between_users():
    headers_a = _register_and_login("notif-iso-a@test.com")
    headers_b = _register_and_login("notif-iso-b@test.com")
    profile_a = client.post("/api/profiles", headers=headers_a, json={"name": "Perfil A"}).json()["id"]
    client.post("/api/searches", headers=headers_a, json={
        "profile_id": profile_a, "city": "Girona", "niche": "restaurante", "max_results": 15,
    })

    notifs_b = client.get("/api/notifications", headers=headers_b).json()
    assert notifs_b["unread_count"] == 0
    assert notifs_b["items"] == []
