"""owner_user_id y aislamiento multi-tenant

Introduce el aislamiento de datos entre clientes: cada negocio (Business)
pasa a pertenecer a un usuario concreto (owner_user_id).

⚠️ SOLO PARA POSTGRESQL. Esta migración usa ALTER TABLE / constraints y SQL
(ANY(:ids)) que SQLite no soporta. Un incidente real ocurrió por ejecutar
una versión anterior de esta migración contra SQLite en producción sin
querer, así que ahora se rechaza explícitamente al arrancar si el dialecto
de la conexión no es 'postgresql' — no depende solo de comprobaciones
externas (Dockerfile, env.py), es una segunda barrera dentro de la propia
migración, por si se ejecuta 'alembic upgrade head' manualmente sin pasar
por el punto de entrada normal.

Estrategia (segura para no perder integridad referencial):
  1. Añade la columna como NULLABLE.
  2. Backfill del propietario de cada negocio existente recorriendo
     business -> search -> prospecting_profile -> user.
  3. Elimina negocios sin propietario deducible (y sus dependencias) —
     no existe ningún propietario legítimo al que asignárselos.
  4. Solo entonces: NOT NULL + índice + nueva restricción de unicidad
     (place_id, owner_user_id) + clave foránea.

Revision ID: 2b4dc6ac964b
Revises: cc333fa260ae
Create Date: 2026-08-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '2b4dc6ac964b'
down_revision: Union[str, None] = 'cc333fa260ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHILD_TABLES = [
    "business_contacts", "website_audits", "opportunities", "lead_scores",
    "activities", "tasks", "message_drafts",
]


def _require_postgresql():
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect != "postgresql":
        raise RuntimeError(
            f"\n\nESTA MIGRACIÓN ('{revision}') SOLO PUEDE EJECUTARSE CONTRA "
            f"POSTGRESQL.\nEl motor detectado es '{dialect}'.\n\n"
            "Esta migración usa ALTER TABLE y SQL específico de Postgres que "
            "no funciona en SQLite. Si ves este error, significa que "
            "DATABASE_URL todavía apunta a SQLite. Configura la base de "
            "datos PostgreSQL en Render (ver RENDER_DEPLOY.md) antes de "
            "continuar. NO se ha modificado nada.\n"
        )


def upgrade() -> None:
    _require_postgresql()
    conn = op.get_bind()

    # 1) Columna nullable de momento.
    op.add_column("businesses", sa.Column("owner_user_id", sa.String(), nullable=True))

    # 2) Backfill: business -> search -> prospecting_profile -> user
    conn.execute(sa.text("""
        UPDATE businesses AS b
        SET owner_user_id = pp.user_id
        FROM searches AS s
        JOIN prospecting_profiles AS pp ON pp.id = s.profile_id
        WHERE b.search_id = s.id
          AND b.owner_user_id IS NULL
    """))

    # 3) Eliminar negocios huérfanos (sin propietario deducible) y sus dependencias.
    orphan_ids = [row[0] for row in conn.execute(sa.text(
        "SELECT id FROM businesses WHERE owner_user_id IS NULL"
    )).fetchall()]

    if orphan_ids:
        for table in _CHILD_TABLES:
            conn.execute(
                sa.text(f"DELETE FROM {table} WHERE business_id = ANY(:ids)"),
                {"ids": orphan_ids},
            )
        conn.execute(
            sa.text("DELETE FROM businesses WHERE id = ANY(:ids)"),
            {"ids": orphan_ids},
        )

    # 4) NOT NULL + índices + nueva restricción de unicidad por cliente.
    op.alter_column("businesses", "owner_user_id", nullable=False)
    op.drop_constraint("uq_business_place_id", "businesses", type_="unique")
    op.create_index("ix_business_owner", "businesses", ["owner_user_id"], unique=False)
    op.create_unique_constraint(
        "uq_business_place_id_per_owner", "businesses", ["place_id", "owner_user_id"]
    )
    op.create_foreign_key(
        "fk_businesses_owner_user_id", "businesses", "users", ["owner_user_id"], ["id"]
    )


def downgrade() -> None:
    _require_postgresql()
    op.drop_constraint("fk_businesses_owner_user_id", "businesses", type_="foreignkey")
    op.drop_constraint("uq_business_place_id_per_owner", "businesses", type_="unique")
    op.drop_index("ix_business_owner", table_name="businesses")
    op.create_unique_constraint("uq_business_place_id", "businesses", ["place_id"])
    op.drop_column("businesses", "owner_user_id")
