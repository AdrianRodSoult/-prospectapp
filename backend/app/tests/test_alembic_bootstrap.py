"""
Tests del caso: conectar Postgres nuevo, dejar que el código antiguo (sin
Alembic) cree el esquema con create_all(), y luego comprobar que el
bootstrap lo detecta y lo marca sin recrear ni borrar nada.
"""
from sqlalchemy import create_engine, text

from app.core.alembic_bootstrap import schema_predates_alembic


def _make_sqlite_engine(tmp_path):
    db_path = tmp_path / "bootstrap_test.db"
    return create_engine(f"sqlite:///{db_path}")


def test_detects_schema_without_alembic_version(tmp_path, monkeypatch):
    engine = _make_sqlite_engine(tmp_path)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE businesses (id TEXT PRIMARY KEY)"))

    import app.core.alembic_bootstrap as bootstrap_mod
    monkeypatch.setattr(bootstrap_mod, "engine", engine)

    assert schema_predates_alembic() is True


def test_fresh_database_is_not_flagged(tmp_path, monkeypatch):
    engine = _make_sqlite_engine(tmp_path)  # sin ninguna tabla

    import app.core.alembic_bootstrap as bootstrap_mod
    monkeypatch.setattr(bootstrap_mod, "engine", engine)

    assert schema_predates_alembic() is False


def test_already_managed_by_alembic_is_not_flagged(tmp_path, monkeypatch):
    engine = _make_sqlite_engine(tmp_path)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE businesses (id TEXT PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))

    import app.core.alembic_bootstrap as bootstrap_mod
    monkeypatch.setattr(bootstrap_mod, "engine", engine)

    assert schema_predates_alembic() is False
