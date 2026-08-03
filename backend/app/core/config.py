"""
Configuración central. Todo se lee de variables de entorno.
Si faltan credenciales, la app funciona en modo MOCK (datos de demostración),
nunca inventa datos "reales" — los marca explícitamente como demo.
"""
import os
from functools import lru_cache


class Settings:
    # --- General ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-insecure-secret-change-me")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./prospectapp.db")

    # --- Google Places ---
    GOOGLE_PLACES_API_KEY: str | None = os.getenv("GOOGLE_PLACES_API_KEY")

    @property
    def PLACES_MODE(self) -> str:
        return "live" if self.GOOGLE_PLACES_API_KEY else "mock"

    # --- IA ---
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")  # mock | anthropic | openai
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    AI_MODEL: str = os.getenv("AI_MODEL", "claude-sonnet-4-6")
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "800"))

    @property
    def AI_MODE(self) -> str:
        if self.AI_PROVIDER == "anthropic" and self.ANTHROPIC_API_KEY:
            return "anthropic"
        if self.AI_PROVIDER == "openai" and self.OPENAI_API_KEY:
            return "openai"
        return "mock"

    # --- Gmail OAuth ---
    GOOGLE_OAUTH_CLIENT_ID: str | None = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI: str = os.getenv(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/gmail/callback"
    )

    @property
    def GMAIL_MODE(self) -> str:
        return "live" if self.GOOGLE_OAUTH_CLIENT_ID else "mock"

    # --- Crawler / seguridad ---
    CRAWLER_MAX_PAGES_PER_DOMAIN: int = int(os.getenv("CRAWLER_MAX_PAGES_PER_DOMAIN", "6"))
    CRAWLER_TIMEOUT_SECONDS: int = int(os.getenv("CRAWLER_TIMEOUT_SECONDS", "8"))
    CRAWLER_MAX_RESPONSE_BYTES: int = int(os.getenv("CRAWLER_MAX_RESPONSE_BYTES", str(2_000_000)))

    # --- Límites de coste ---
    DAILY_SEARCH_LIMIT: int = int(os.getenv("DAILY_SEARCH_LIMIT", "50"))
    MAX_RESULTS_PER_SEARCH: int = int(os.getenv("MAX_RESULTS_PER_SEARCH", "60"))

    # --- CORS ---
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


@lru_cache
def get_settings() -> Settings:
    return Settings()
