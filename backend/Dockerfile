FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Cuatro pasos encadenados con && : si CUALQUIERA falla, el contenedor no
# arranca el servidor.
#   1) Gate explícito: bloquea si es producción y el motor sigue siendo SQLite.
#   2) Bootstrap: si el esquema ya existía (creado por código anterior a
#      Alembic), lo marca como aplicado SIN recrear ninguna tabla.
#   3) Migraciones (baseline si hace falta, y multi-tenant).
#   4) Arrancar el servidor, solo si todo lo anterior tuvo éxito.
CMD ["sh", "-c", "python -m app.core.db_engine_guard && python -m app.core.alembic_bootstrap && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
