# Procedimiento seguro: PostgreSQL persistente + aislamiento multi-tenant

> **Contexto:** el primer intento de este cambio (PR #2) provocó una caída
> en producción porque Render desplegó y ejecutó las migraciones antes de
> que `DATABASE_URL` apuntara realmente a Postgres — la migración
> multi-tenant contiene SQL específico de Postgres que SQLite no soporta.
> Ese PR ya fue revertido. Este documento describe el procedimiento
> corregido, con barreras técnicas (no solo instrucciones escritas) que
> impiden que eso vuelva a pasar.

## Qué cambió respecto al intento anterior

1. **Gate explícito antes de migrar.** El arranque ahora ejecuta
   `python -m app.core.db_engine_guard` antes que nada. Si detecta que
   estamos en un entorno de producción (`APP_ENV=production` o la variable
   `RENDER=true` que Render inyecta automáticamente) y `DATABASE_URL`
   sigue siendo SQLite, **se detiene con código de error y no llega ni a
   intentar ninguna migración.**
2. **Bloqueo también dentro de la propia migración multi-tenant**, como
   segunda barrera independiente: si alguien ejecuta `alembic upgrade head`
   manualmente sin pasar por el gate, la migración en sí rechaza correr
   si el dialecto de la conexión no es `postgresql`.
3. **Logging explícito del motor** en cada arranque de Alembic y en el
   gate, visible directamente en los logs de Render sin necesitar acceso
   a la base de datos.
4. Todo esto se probó de verdad en ambos sentidos (bloqueo con SQLite,
   éxito con Postgres) contra un Postgres 16 real, no simulado.

## Paso a paso — hazlo EN ESTE ORDEN

### 1. Crear la base de datos Postgres en Render

1. Panel de Render → **New** → **PostgreSQL**.
2. Nombre sugerido: `prospectapp-db`. Región: la misma que tu backend.
3. Una vez creada, copia el valor **"Internal Database URL"** (no el
   "External"): formato `postgres://usuario:password@host-interno/nombre_bd`.

### 2. Configurar el backend — TODAVÍA NO despliegues

En el servicio del backend → **Environment**, añade:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | La *Internal Database URL* del paso 1 |
| `SECRET_KEY` | Una clave larga y aleatoria (si no la tienes ya) |

**No despliegues todavía.** Ve al paso 3 primero.

### 3. Verificar el motor ANTES de mergear (punto #3 de tu petición)

Antes de aprobar el merge de esta rama a `main`, con la rama actual ya
desplegada (el código del gate no requiere el merge para funcionar, ya
que es solo lectura de `DATABASE_URL`), puedes comprobar en los logs de
Render qué motor detecta la app. Búscalo en el log del backend:

```
[prospectapp] Motor de base de datos detectado: 'postgresql' (entorno: PRODUCCIÓN)
```

Si en vez de `postgresql` ves `sqlite`, **no continúes**: revisa que la
variable `DATABASE_URL` del paso 2 se guardó correctamente en Render.

### 4. Mergear y desplegar

Con `DATABASE_URL` ya confirmado como Postgres en logs, aprueba el merge.
El despliegue automático ejecutará, en este orden exacto (garantizado por
el `Dockerfile`):

```
python -m app.core.db_engine_guard   # (punto #1: bloquea si sigue en SQLite)
  && alembic upgrade head             # (puntos #4 y #5: baseline primero, multi-tenant después — en ese orden fijo por la cadena de revisiones de Alembic)
  && uvicorn app.main:app ...         # solo arranca si todo lo anterior funcionó
```

### 5. Qué pasa con tus datos (punto #7 de tu petición)

**Nada se modifica ni se elimina hasta que el gate confirme Postgres.**
Si el gate bloquea (sigues en SQLite), la cadena `&&` se corta ahí: no se
ejecuta ninguna migración, ni el baseline, ni la multi-tenant, ni se toca
ni una fila.

Solo cuando `DATABASE_URL` apunta de verdad a Postgres:
- El usuario real que ya creaste **no se toca ni se borra**.
- Si tuvieras algún negocio de prueba guardado con búsqueda asociada, la
  migración le asigna automáticamente el propietario correcto (probado
  con datos que simulan exactamente tu caso).
- Si hubiera negocios sin búsqueda asociada (huérfanos, no debería haber
  ninguno), se eliminarían junto con sus dependencias — ya confirmaste que
  no hay datos comerciales importantes que conservar.

### 6. Verificación después de desplegar

1. Revisa los logs de Render: debe aparecer `'postgresql'` y las dos líneas
   `Running upgrade ... baseline...` y `Running upgrade ... multi-tenant...`.
2. Entra a la app, confirma que tu login sigue funcionando.
3. Haz una búsqueda nueva y compruébala en `/results`.
4. (Opcional) Registra un segundo usuario de prueba, busca el mismo nicho/
   ciudad, y confirma que no ve los negocios del primero.

## Plan de rollback (punto #6 de tu petición)

**Si el despliegue falla en el gate (paso 1):** no hay nada que revertir —
el servidor simplemente no arranca con la versión nueva, y Render sigue
sirviendo la última versión que funcionaba. Corrige `DATABASE_URL` y
vuelve a desplegar.

**Si necesitas revertir después de un despliegue exitoso:**

- *Solo el código* (sin tocar el esquema): **Manual Deploy → Redeploy**
  en Render sobre el commit anterior a este merge.
- *El esquema también* (volver a quitar `owner_user_id`, por ejemplo si
  detectas un problema de datos): desde un entorno con acceso a
  `DATABASE_URL` de producción:
  ```
  alembic downgrade -1
  ```
  Esto revierte solo la migración multi-tenant (mantiene el baseline).
  La función `downgrade()` de esa migración también rechaza correr si el
  dialecto no es Postgres, por la misma razón de seguridad.

## Comprobación conjunta antes de mergear

Tal como pediste, no se abre ningún Pull Request pidiendo merge hasta
que confirmemos juntos, paso a paso:

- [ ] Postgres creado en Render (paso 1)
- [ ] `DATABASE_URL` configurado en el backend (paso 2)
- [ ] Log confirmado mostrando `'postgresql'` (paso 3)
- [ ] Tú das el visto bueno para que publique la rama y abramos el PR
