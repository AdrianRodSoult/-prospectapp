"""
Tests del incidente: bloquear la migración multi-tenant (y el arranque en
general) si producción sigue usando SQLite en vez de PostgreSQL.
"""
import pytest

from app.core.db_engine_guard import get_database_engine_name


def test_detects_sqlite_engine():
    assert get_database_engine_name("sqlite:///./file.db") == "sqlite"


def test_detects_postgresql_engine():
    assert get_database_engine_name("postgresql://user:pass@host/db") == "postgresql"


def test_detects_postgresql_engine_legacy_scheme():
    # Antes de la normalización de config.py, así llega la URL desde Render.
    assert get_database_engine_name("postgres://user:pass@host/db") == "postgres"


def test_require_postgres_blocks_sqlite_in_production(monkeypatch):
    import app.core.db_engine_guard as guard

    class FakeSettings:
        DATABASE_URL = "sqlite:///./prod.db"

    monkeypatch.setattr(guard, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(guard, "_is_production_like", lambda: True)

    with pytest.raises(SystemExit) as exc_info:
        guard.require_postgres_in_production()
    assert exc_info.value.code == 1


def test_require_postgres_allows_sqlite_outside_production(monkeypatch):
    import app.core.db_engine_guard as guard

    class FakeSettings:
        DATABASE_URL = "sqlite:///./dev.db"

    monkeypatch.setattr(guard, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(guard, "_is_production_like", lambda: False)

    guard.require_postgres_in_production()  # no debe lanzar SystemExit


def test_require_postgres_allows_postgres_in_production(monkeypatch):
    import app.core.db_engine_guard as guard

    class FakeSettings:
        DATABASE_URL = "postgresql://user:pass@host/db"

    monkeypatch.setattr(guard, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(guard, "_is_production_like", lambda: True)

    guard.require_postgres_in_production()  # no debe lanzar SystemExit
