"""owner_user_id y aislamiento multi-tenant

Esta migración introduce el aislamiento de datos entre clientes: cada
negocio (Business) pasa a pertenecer a un usuario concreto (owner_user_id),
y dos clientes que buscan el mismo lugar real ya NO comparten fila.

Estrategia segura para no perder integridad referencial ni romper el
arranque de la app si ya existen negocios guardados:
  1. Añade la columna como NULLABLE (no se puede meter NOT NULL de golpe
     si ya hay filas).
  2. Rellena (backfill) el propietario de cada negocio existente
     recorriendo business -> search -> prospecting_profile -> user,
     que es la única cadena de propiedad fiable con el esquema actual.
  3. Cualquier negocio para el que no se pueda deducir un propietario
     (por ejemplo, negocios sin búsqueda asociada) se elimina, junto con
     sus filas dependientes (contactos, auditoría, oportunidades, score,
     actividad, tareas, borradores de mensaje). Esto es deliberado: no
     existe ningún propietario legítimo al que asignárselo, y ya se
     confirmó que no hay datos comerciales importantes que conservar.
  4. Solo entonces se pone la columna en NOT NULL y se crean los índices
     y la nueva restricción de unicidad (place_id, owner_user_id).

Revision ID: 9695e5535984
Revises: ca257c57dab4
Create Date: 2026-08-04 22:51:48.621386
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9695e5535984'
down_revision: Union[str, None] = 'ca257c57dab4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tablas hijas de "businesses" que hay que limpiar si se borra un negocio huérfano.
_CHILD_TABLES = [
    "business_contacts", "website_audits", "opportunities", "lead_scores",
    "activities", "tasks", "message_drafts",
]


def upgrade() -> None:
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

    # 4) Ahora sí, NOT NULL + índices + nueva restricción de unicidad por cliente.
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
    op.drop_constraint("fk_businesses_owner_user_id", "businesses", type_="foreignkey")
    op.drop_constraint("uq_business_place_id_per_owner", "businesses", type_="unique")
    op.drop_index("ix_business_owner", table_name="businesses")
    op.create_unique_constraint("uq_business_place_id", "businesses", ["place_id"])
    op.drop_column("businesses", "owner_user_id")
