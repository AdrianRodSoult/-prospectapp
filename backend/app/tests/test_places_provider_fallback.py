"""
Tests del fallback automático: si Google Places está configurado pero falla
(clave inválida, cuota agotada, red caída), la búsqueda debe recurrir al
modo demo automáticamente, y SIEMPRE marcarlo explícitamente (nunca debe
presentarse un dato de demostración como si fuera real).
"""
import pytest

from app.providers.business_data_provider import (
    search_with_fallback, GooglePlacesProvider, MockPlacesProvider,
)


def test_fallback_triggers_when_live_provider_fails(monkeypatch):
    def _boom(self, *args, **kwargs):
        raise RuntimeError("Error consultando Google Places API: 401 Unauthorized")

    monkeypatch.setattr(GooglePlacesProvider, "search", _boom)
    monkeypatch.setattr(
        "app.providers.business_data_provider.settings.GOOGLE_PLACES_API_KEY", "clave-invalida"
    )

    result = search_with_fallback("Algeciras", "peluquería", None, 5.0, 10)

    assert result.fallback_used is True
    assert "Google Places" in result.limitations
    assert len(result.businesses) > 0  # el usuario sigue recibiendo resultados demo, no un error


def test_no_fallback_flag_in_normal_mock_mode(monkeypatch):
    monkeypatch.setattr(
        "app.providers.business_data_provider.settings.GOOGLE_PLACES_API_KEY", None
    )
    result = search_with_fallback("Cadiz", "restaurante", None, 5.0, 10)
    assert result.fallback_used is False
    assert result.source == MockPlacesProvider.name


def test_mock_provider_itself_never_raises_as_fallback_source(monkeypatch):
    """Si el propio modo demo fallara (no debería), no hay a qué recurrir: debe propagar el error."""
    def _boom(self, *args, **kwargs):
        raise RuntimeError("fallo inesperado en el propio mock")

    monkeypatch.setattr(MockPlacesProvider, "search", _boom)
    monkeypatch.setattr(
        "app.providers.business_data_provider.settings.GOOGLE_PLACES_API_KEY", None
    )
    with pytest.raises(RuntimeError):
        search_with_fallback("Cadiz", "restaurante", None, 5.0, 10)
