"""
Arquitectura de proveedores intercambiables para descubrimiento de negocios.
Cada proveedor debe declarar: fuente, fecha de consulta, campos recuperados,
confianza, coste estimado, limitaciones y términos aplicables.
"""
from __future__ import annotations

import abc
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


@dataclass
class ProviderResult:
    source: str
    queried_at: datetime
    fields_retrieved: list[str]
    confidence: str
    estimated_cost_usd: float
    limitations: str
    terms_reference: str
    businesses: list[dict[str, Any]] = field(default_factory=list)
    # Se rellenan solo cuando una fuente en vivo falla y se recurre al modo demo.
    fallback_used: bool = False
    fallback_reason: str | None = None


class BusinessDataProvider(abc.ABC):
    """Interfaz común. Cualquier fuente nueva debe implementar esto."""

    name: str

    @abc.abstractmethod
    def search(self, city: str, niche: str, region: str | None, radius_km: float,
               max_results: int) -> ProviderResult:
        ...


class GooglePlacesProvider(BusinessDataProvider):
    """
    Proveedor real usando Google Places API (Text Search + Place Details),
    con field masks para minimizar coste. Requiere GOOGLE_PLACES_API_KEY.
    Docs: https://developers.google.com/maps/documentation/places/web-service
    """
    name = "google_places_api"
    TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

    FIELD_MASK = ",".join([
        "places.id", "places.displayName", "places.formattedAddress",
        "places.location", "places.internationalPhoneNumber",
        "places.websiteUri", "places.rating", "places.userRatingCount",
        "places.regularOpeningHours", "places.currentOpeningHours",
        "places.priceLevel", "places.googleMapsUri", "places.primaryType",
    ])

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, city: str, niche: str, region: str | None, radius_km: float,
               max_results: int) -> ProviderResult:
        query = f"{niche} en {city}" + (f", {region}" if region else "")
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        body = {"textQuery": query, "maxResultCount": min(max_results, 20)}
        businesses: list[dict[str, Any]] = []
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(self.TEXT_SEARCH_URL, headers=headers, json=body)
                resp.raise_for_status()
                data = resp.json()
                for place in data.get("places", []):
                    businesses.append(self._map_place(place))
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Error consultando Google Places API: {exc}") from exc

        # Coste aproximado: Text Search (Pro SKU) ~ $0.032 / solicitud (revisar precios oficiales)
        estimated_cost = 0.032 * (1 + len(businesses) // 20)

        return ProviderResult(
            source=self.name,
            queried_at=datetime.utcnow(),
            fields_retrieved=self.FIELD_MASK.split(","),
            confidence="verified",
            estimated_cost_usd=round(estimated_cost, 4),
            limitations="Sujeto a cuota diaria y a los Términos de Servicio de Google Places API.",
            terms_reference="https://developers.google.com/maps/documentation/places/web-service/policies",
            businesses=businesses,
        )

    @staticmethod
    def _map_place(place: dict) -> dict:
        loc = place.get("location", {})
        return {
            "place_id": place.get("id"),
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "phone_intl": place.get("internationalPhoneNumber"),
            "website_url": place.get("websiteUri"),
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
            "google_maps_url": place.get("googleMapsUri"),
            "category": place.get("primaryType"),
            "opening_hours": place.get("regularOpeningHours"),
            "is_open_now": (place.get("currentOpeningHours") or {}).get("openNow"),
        }


class MockPlacesProvider(BusinessDataProvider):
    """
    Proveedor de demostración. Genera negocios ficticios realistas para
    desarrollar y probar todo el flujo SIN gastar nada ni requerir API key.
    Todos los datos se marcan con source=demo_mock y NUNCA se presentan
    como reales en la interfaz.
    """
    name = "demo_mock"

    _NAME_TEMPLATES = [
        "Peluquería {n}", "Salón de Belleza {n}", "Estudio Look {n}",
        "Barbería {n}", "Centro Estético {n}",
    ]
    _STREETS = ["Calle Real", "Avenida del Mar", "Calle Larga", "Plaza Mayor", "Calle Sol"]

    def search(self, city: str, niche: str, region: str | None, radius_km: float,
               max_results: int) -> ProviderResult:
        rng = random.Random(f"{city}-{niche}")
        count = min(max_results, 20)
        businesses = []
        for i in range(count):
            has_website = rng.random() > 0.45
            name = rng.choice(self._NAME_TEMPLATES).format(n=chr(65 + i % 26))
            businesses.append({
                "place_id": f"mock-{city.lower()}-{niche.lower()}-{i}".replace(" ", "-"),
                "name": f"{name} {city}",
                "address": f"{rng.choice(self._STREETS)} {rng.randint(1, 150)}, {city}",
                "latitude": 36.13 + rng.uniform(-0.05, 0.05),
                "longitude": -5.45 + rng.uniform(-0.05, 0.05),
                "phone_intl": f"+34 6{rng.randint(10000000, 99999999)}",
                "website_url": f"https://www.{name.lower().replace(' ', '')}{i}.demo" if has_website else None,
                "rating": round(rng.uniform(3.2, 5.0), 1),
                "review_count": rng.randint(3, 350),
                "google_maps_url": f"https://maps.google.com/?cid=mock{i}",
                "category": niche,
                "opening_hours": None,
                "is_open_now": rng.random() > 0.3,
            })
        return ProviderResult(
            source=self.name,
            queried_at=datetime.utcnow(),
            fields_retrieved=["place_id", "name", "address", "phone_intl", "website_url",
                               "rating", "review_count"],
            confidence="not_verified",
            estimated_cost_usd=0.0,
            limitations="Datos de DEMOSTRACIÓN generados localmente. No representan negocios reales.",
            terms_reference="n/a (modo demo)",
            businesses=businesses,
        )


def get_places_provider(user_api_key: str | None = None) -> BusinessDataProvider:
    """
    Prioridad: la API key propia del cliente (si la configuró) por encima
    de la del servidor. Así cada cliente usa su propia cuota y factura de
    Google, y un cliente sin key propia sigue funcionando en modo demo
    (o con la key global del servidor, si existiera, como antes).
    """
    effective_key = user_api_key or settings.GOOGLE_PLACES_API_KEY
    if effective_key:
        return GooglePlacesProvider(api_key=effective_key)
    return MockPlacesProvider()


def search_with_fallback(city: str, niche: str, region: str | None, radius_km: float,
                          max_results: int, user_api_key: str | None = None) -> ProviderResult:
    """
    Intenta la búsqueda con el proveedor configurado (real si hay API key,
    priorizando la propia del cliente sobre la del servidor). Si el
    proveedor real falla (clave inválida, cuota agotada, red caída),
    recurre automáticamente al modo demo para que la búsqueda no rompa la
    experiencia del usuario, pero SIEMPRE marca el resultado como fallback
    (nunca se presenta un dato de demostración como si fuera real).
    """
    provider = get_places_provider(user_api_key)
    try:
        return provider.search(city, niche, region, radius_km, max_results)
    except RuntimeError as exc:
        if provider.name == MockPlacesProvider.name:
            raise  # el propio modo demo no debería fallar; no hay a qué recurrir
        fallback_result = MockPlacesProvider().search(city, niche, region, radius_km, max_results)
        fallback_result.fallback_used = True
        fallback_result.fallback_reason = str(exc)
        fallback_result.limitations = (
            "Google Places no respondió correctamente, así que se muestran datos de "
            "DEMOSTRACIÓN como respaldo. " + fallback_result.limitations
        )
        return fallback_result
