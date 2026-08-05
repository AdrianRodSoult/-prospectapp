FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Tres pasos encadenados con && : si CUALQUIERA falla, el contenedor no
# arranca el servidor (evita el incidente de ejecutar una migración de
# Postgres contra SQLite):
#   1) Gate explícito: bloquea si es producción y el motor sigue siendo SQLite.
#   2) Migraciones (baseline, y solo si el gate pasó, la de multi-tenant).
#   3) Arrancar el servidor, solo si los dos pasos anteriores tuvieron éxito.
CMD ["sh", "-c", "python -m app.core.db_engine_guard && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
