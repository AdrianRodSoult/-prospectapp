"""
Detección del motor de base de datos y barrera de seguridad.

Este módulo existe por un incidente real: una migración con SQL específico
de PostgreSQL se ejecutó por error contra SQLite en producción (porque
DATABASE_URL no se había cambiado todavía), tumbando el backend.

A partir de ahora, NADA que dependa de Postgres se ejecuta sin que este
módulo lo confirme explícitamente primero. No hay "modo silencioso": si
algo no cuadra, se detiene con un mensaje claro en vez de fallar a medias.
"""
import sys

from app.core.config import get_settings


def get_database_engine_name(database_url: str) -> str:
    """Devuelve 'sqlite', 'postgresql' o el esquema tal cual si es otro."""
    return database_url.split("://", 1)[0].split("+", 1)[0]


def _is_production_like() -> bool:
    """Mismo criterio que config._is_production_environment(): APP_ENV=production
    o la variable RENDER=true que Render inyecta automáticamente en sus servicios."""
    import os
    if os.getenv("APP_ENV", "development") == "production":
        return True
    if os.getenv("RENDER", "").lower() == "true":
        return True
    return False


def log_database_engine() -> str:
    """
    Escribe en stdout (visible en los logs de Render) qué motor de base de
    datos está usando la app realmente. Este es el punto #3 del procedimiento:
    verificar por logs qué motor está en uso, sin necesitar acceso directo
    a la base de datos.
    """
    settings = get_settings()
    engine_name = get_database_engine_name(settings.DATABASE_URL)
    env_label = "PRODUCCIÓN" if _is_production_like() else "desarrollo/test"
    print(
        f"[prospectapp] Motor de base de datos detectado: '{engine_name}' "
        f"(entorno: {env_label})",
        file=sys.stderr,
    )
    return engine_name


def require_postgres_in_production() -> None:
    """
    Punto #1 del procedimiento: bloquea CUALQUIER intento de migrar si
    estamos en un entorno de producción y el motor configurado sigue
    siendo SQLite. Debe llamarse ANTES de ejecutar ninguna migración.

    Sale del proceso con código de error distinto de 0 (para que el
    comando de arranque en Render/Docker se detenga ahí, sin llegar a
    ejecutar 'alembic upgrade head').
    """
    settings = get_settings()
    engine_name = log_database_engine()

    if _is_production_like() and engine_name == "sqlite":
        print(
            "\n"
            "════════════════════════════════════════════════════════════════\n"
            " BLOQUEADO: DATABASE_URL sigue siendo SQLite en un entorno de\n"
            " producción. Las migraciones NO se van a ejecutar.\n"
            "\n"
            " Esto es intencional: ejecutar una migración pensada para\n"
            " PostgreSQL contra SQLite puede tumbar el servicio (ya pasó\n"
            " una vez). Antes de continuar:\n"
            "\n"
            "   1. Crea una base PostgreSQL en Render.\n"
            "   2. Copia su 'Internal Database URL'.\n"
            "   3. Configura DATABASE_URL en el servicio backend con ese valor.\n"
            "   4. Vuelve a desplegar.\n"
            "\n"
            " Instrucciones exactas en RENDER_DEPLOY.md.\n"
            "════════════════════════════════════════════════════════════════\n",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    # Se ejecuta como script independiente desde el comando de arranque,
    # ANTES de 'alembic upgrade head'. Ver backend/Dockerfile.
    require_postgres_in_production()
    print("[prospectapp] Comprobación de motor de base de datos: OK.", file=sys.stderr)
