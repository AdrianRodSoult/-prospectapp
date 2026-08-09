"""
Prueba el rate limiting en sí, de forma aislada del resto de tests
funcionales (que lo desactivan para no interferir entre ellos).
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_prospectapp_ratelimit.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402

client = TestClient(app)


def setup_function():
    limiter.enabled = True
    limiter.reset()


def teardown_function():
    limiter.reset()
    limiter.enabled = False  # deja el estado como lo esperan el resto de tests


def test_login_blocks_after_too_many_attempts():
    # El límite es 5/minuto. Los primeros 5 intentos (con credenciales
    # incorrectas) deben devolver 401 normal; el 6º debe ser 429.
    for _ in range(5):
        resp = client.post("/api/auth/login", data={"username": "nadie@test.com", "password": "mal"})
        assert resp.status_code == 401

    resp = client.post("/api/auth/login", data={"username": "nadie@test.com", "password": "mal"})
    assert resp.status_code == 429


def test_register_blocks_after_too_many_attempts():
    # El límite es 3/hora.
    for i in range(3):
        resp = client.post("/api/auth/register", json={
            "email": f"ratelimit{i}@test.com", "password": "test1234",
        })
        assert resp.status_code == 200

    resp = client.post("/api/auth/register", json={
        "email": "ratelimit-extra@test.com", "password": "test1234",
    })
    assert resp.status_code == 429
