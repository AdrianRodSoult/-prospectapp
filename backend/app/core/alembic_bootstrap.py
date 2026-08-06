"""
Bootstrap de transición Alembic.

Contexto: antes de introducir Alembic, la app creaba las tablas con
Base.metadata.create_all() en cada arranque. Si el usuario conecta una
base PostgreSQL nueva ANTES de mergear las migraciones (para comprobar
la conexión primero, con el código antiguo todavía desplegado), ese
código antiguo va a crear el esquema "baseline" con create_all().

Cuando después lleguen las migraciones de Alembic, la migración baseline
intentaría CREATE TABLE sobre tablas que ya existen, y fallaría con
"relation already exists" — un fallo distinto pero igual de bloqueante
que el incidente original.

Este módulo detecta exactamente ese caso y lo resuelve de la única forma
segura posible: sin borrar ni recrear nada, simplemente le dice a Alembic
"la migración baseline ya está aplicada" (alembic stamp), y a partir de
ahí Alembic sigue con el resto de migraciones con normalidad.

No se ejecuta NUNCA ningún DROP ni CREATE destructivo desde aquí.
"""
import subprocess
import sys

from sqlalchemy import inspect

from app.core.database import engine

# Debe coincidir con el revision id de la migración baseline.
BASELINE_REVISION = "cc333fa260ae"

# Una tabla que solo existiría si el esquema baseline ya fue creado
# (por Alembic o por el create_all() del código antiguo).
_MARKER_TABLE = "businesses"


def schema_predates_alembic() -> bool:
    """
    True si el esquema ya existe (tabla 'businesses' presente) pero Alembic
    todavía no lo sabe (no existe la tabla alembic_version). Ese es
    exactamente el estado que deja el código antiguo con create_all().
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    return _MARKER_TABLE in tables and "alembic_version" not in tables


def stamp_baseline_if_needed() -> None:
    """
    Si detecta el caso de arriba, ejecuta 'alembic stamp <baseline>' —
    NUNCA 'alembic upgrade', para no re-ejecutar ningún CREATE TABLE.
    Si el esquema es nuevo de verdad (Postgres recién creado, sin
    ninguna tabla), no hace nada: Alembic aplicará baseline con
    normalidad, como en cualquier base nueva.
    """
    if not schema_predates_alembic():
        print(
            "[prospectapp] Bootstrap: no hace falta 'stamp' "
            "(esquema nuevo o ya gestionado por Alembic).",
            file=sys.stderr,
        )
        return

    print(
        "[prospectapp] Bootstrap: detectado esquema pre-Alembic (creado por "
        "create_all() del codigo anterior). Marcando la migracion baseline "
        f"('{BASELINE_REVISION}') como ya aplicada, SIN recrear ninguna tabla.",
        file=sys.stderr,
    )
    result = subprocess.run(
        ["alembic", "stamp", BASELINE_REVISION],
        capture_output=True, text=True,
    )
    print(result.stdout, file=sys.stderr)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        print("[prospectapp] Bootstrap: 'alembic stamp' falló. Deteniendo el arranque.",
              file=sys.stderr)
        sys.exit(1)
    print("[prospectapp] Bootstrap: stamp completado correctamente.", file=sys.stderr)


if __name__ == "__main__":
    stamp_baseline_if_needed()
