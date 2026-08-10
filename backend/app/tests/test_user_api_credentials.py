"""
Tests de las API keys propias del cliente: cifrado/descifrado, que nunca
se exponga la clave real, aislamiento entre usuarios, y que los
proveedores prioricen correctamente la key del cliente sobre la del servidor.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_prospectapp_apikeys.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.crypto import encrypt_secret, decrypt_secret  # noqa: E402
from app.providers.business_data_provider import get_places_provider, MockPlacesProvider, GooglePlacesProvider  # noqa: E402
from app.providers.ai_provider import get_ai_provider, MockAIProvider, AnthropicAIProvider, OpenAIProvider  # noqa: E402

limiter.enabled = False
client = TestClient(app)


def _register_and_login(email: str):
    client.post("/api/auth/register", json={"email": email, "password": "test1234"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "test1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_encrypt_decrypt_roundtrip():
    original = "clave-super-secreta-de-google-places"
    encrypted = encrypt_secret(original)
    assert encrypted != original
    assert decrypt_secret(encrypted) == original


def test_status_defaults_to_not_configured():
    headers = _register_and_login("nokeys@test.com")
    resp = client.get("/api/settings/api-keys", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "google_places_configured": False,
        "anthropic_configured": False,
        "openai_configured": False,
    }


def test_saving_key_never_returns_plaintext():
    headers = _register_and_login("savekey@test.com")
    resp = client.put("/api/settings/api-keys", headers=headers, json={
        "google_places_api_key": "AIzaSyD-mi-clave-secreta-de-verdad",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["google_places_configured"] is True
    # La clave real no debe aparecer en ningún campo de la respuesta.
    assert "AIzaSyD-mi-clave-secreta-de-verdad" not in resp.text


def test_empty_string_deletes_key():
    headers = _register_and_login("deletekey@test.com")
    client.put("/api/settings/api-keys", headers=headers, json={"anthropic_api_key": "sk-ant-algo"})
    resp = client.put("/api/settings/api-keys", headers=headers, json={"anthropic_api_key": ""})
    assert resp.json()["anthropic_configured"] is False


def test_keys_isolated_between_users():
    headers_a = _register_and_login("keys-a@test.com")
    headers_b = _register_and_login("keys-b@test.com")

    client.put("/api/settings/api-keys", headers=headers_a, json={"openai_api_key": "sk-de-la-empresa-a"})

    status_b = client.get("/api/settings/api-keys", headers=headers_b).json()
    assert status_b["openai_configured"] is False  # B no ve ni hereda la key de A


def test_places_provider_prioritizes_user_key_over_mock():
    provider = get_places_provider(user_api_key="clave-propia-del-cliente")
    assert isinstance(provider, GooglePlacesProvider)
    assert provider.api_key == "clave-propia-del-cliente"


def test_places_provider_falls_back_to_mock_without_any_key():
    provider = get_places_provider(user_api_key=None)
    assert isinstance(provider, MockPlacesProvider)


def test_ai_provider_prioritizes_user_anthropic_key():
    provider = get_ai_provider(user_anthropic_key="sk-ant-propia", user_openai_key=None)
    assert isinstance(provider, AnthropicAIProvider)
    assert provider.api_key == "sk-ant-propia"


def test_ai_provider_prioritizes_user_openai_key():
    provider = get_ai_provider(user_anthropic_key=None, user_openai_key="sk-propia-openai")
    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "sk-propia-openai"


def test_ai_provider_falls_back_to_mock_without_any_key():
    provider = get_ai_provider(user_anthropic_key=None, user_openai_key=None)
    assert isinstance(provider, MockAIProvider)


def test_decrypt_returns_none_for_garbage_instead_of_crashing():
    assert decrypt_secret("esto-no-es-un-token-fernet-valido") is None
