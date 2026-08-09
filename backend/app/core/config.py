"""
Configuración central. Todo se lee de variables de entorno.
Si faltan credenciales, la app funciona en modo MOCK (datos de demostración),
nunca inventa datos "reales" — los marca explícitamente como demo.
"""
import os
from functools import lru_cache

INSECURE_DEFAULT_SECRET_KEY = "dev-insecure-secret-change-me"
MIN_SECRET_KEY_LENGTH = 32


def _normalize_database_url(raw_url: str) -> str:
    """
    Render (y Heroku) entregan la URL de Postgres con el esquema legado
    'postgres://'. SQLAlchemy 2.x solo acepta 'postgresql://'. Sin esta
    normalización, la app fallaría al arrancar en producción con un
    DATABASE_URL de Postgres real, aunque funcionara perfecto en local.
    """
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url


def is_production_environment() -> bool:
    """
    Fuente única de verdad para "¿estamos en producción?", usada tanto
    para validar SECRET_KEY como para el guardia de motor de base de
    datos (app.core.db_engine_guard). Se considera producción si
    APP_ENV=production, o si detectamos que corremos en Render (que
    inyecta RENDER=true automáticamente en todos sus servicios) — esto
    último es un salvavidas por si algún día se despliega sin haber
    configurado APP_ENV a mano.
    """
    if os.getenv("APP_ENV", "development") == "production":
        return True
    if os.getenv("RENDER", "").lower() == "true":
        return True
    return False


def validate_secret_key(secret_key: str, is_production: bool) -> None:
    """
    En producción, un SECRET_KEY débil o por defecto permite a cualquiera
    falsificar tokens JWT de sesión de OTROS usuarios (suplantación total
    de identidad). Por eso el arranque debe fallar de forma ruidosa en
    vez de arrancar "funcionando" con una clave insegura.
    En desarrollo/tests se permite el valor por defecto, para no romper
    el flujo de trabajo local habitual.
    """
    if not is_production:
        return
    if secret_key == INSECURE_DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY no está configurado (se está usando el valor por defecto "
            "inseguro) en un entorno de producción. Configura una variable de "
            "entorno SECRET_KEY con una clave larga y aleatoria antes de arrancar. "
            "Puedes generar una con: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            f"SECRET_KEY es demasiado corto para producción (mínimo "
            f"{MIN_SECRET_KEY_LENGTH} caracteres). Genera uno nuevo con: "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )


class Settings:
    # --- General ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", INSECURE_DEFAULT_SECRET_KEY)
    DATABASE_URL: str = _normalize_database_url(
        os.getenv("DATABASE_URL", "sqlite:///./prospectapp.db")
    )

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
    settings = Settings()
    validate_secret_key(settings.SECRET_KEY, is_production_environment())
    return settings
