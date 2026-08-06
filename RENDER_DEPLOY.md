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

## Paso a paso — hazlo EN ESTE ORDEN (orden conservador: conexión antes que merge)

Este orden es el más seguro posible: primero se comprueba la conexión a
Postgres con el código actual (sin tocar nada del código nuevo), y solo
cuando esa conexión está confirmada se mergea el procedimiento con las
migraciones.

### 1. Crear la base de datos Postgres en Render

1. Panel de Render → **New** → **PostgreSQL**.
2. Nombre sugerido: `prospectapp-db`. Región: la misma que tu backend.
3. Copia el valor **"Internal Database URL"**.

### 2. Configurar DATABASE_URL — TODAVÍA sin mergear nada

En el servicio del backend → **Environment**, pon `DATABASE_URL` con esa
URL. Esto dispara un redeploy **con el código actual** (el que ya está en
`main`, sin Alembic). Ese código sigue usando `create_all()`, así que
creará el esquema en Postgres automáticamente — es normal y esperado,
es justo la comprobación de conexión que quieres hacer.

### 3. Verificar la conexión

- En los logs del backend, confirma que arrancó sin errores.
- Entra a la app y confirma que tu login sigue funcionando (ahora contra
  Postgres, no contra el SQLite anterior).
- Opcional: haz una búsqueda para generar algo de actividad de prueba.

**No mergees nada todavía. Este es el punto de confirmación conjunta.**

### 4. Mergear el procedimiento seguro

Cuando confirmes que el paso 3 funciona, publico la rama
`feature/safe-postgres-migration-procedure` y te paso el enlace del PR.
Al mergearlo, el nuevo `Dockerfile` ejecuta, en este orden exacto:

```
python -m app.core.db_engine_guard      # confirma que sigue siendo Postgres
  && python -m app.core.alembic_bootstrap  # detecta el esquema creado en el paso 2
                                             # y lo marca como "baseline aplicado"
                                             # SIN recrear ni una tabla
  && alembic upgrade head                  # aplica SOLO la migración multi-tenant
  && uvicorn app.main:app ...
```

Esto es importante: como en el paso 2 el código antiguo ya creó las
tablas, la migración baseline **no se vuelve a ejecutar** — el bootstrap
la marca como aplicada y Alembic solo añade lo nuevo (`owner_user_id` y
el aislamiento). Nada se borra ni se recrea. Esto está probado
exactamente contra este escenario (esquema viejo + usuario real ya
insertado), no es teórico.

### 5. Qué pasa con tus datos

- Tu usuario real, creado en el paso 2 contra Postgres (o migrado desde
  SQLite si ya existía antes), **no se toca**.
- Si guardaste algún negocio de prueba con búsqueda asociada, se le
  asigna automáticamente como propietario.
- Cualquier negocio sin búsqueda asociada (no debería haber ninguno) se
  eliminaría — ya confirmaste que no hay datos comerciales que conservar.

### 6. Verificación final

1. Logs: debe verse `'postgresql'`, el mensaje de bootstrap, y
   `Running upgrade cc333fa260ae -> ...multi-tenant`.
2. Login sigue funcionando.
3. Búsqueda nueva funciona.
4. (Opcional) Segundo usuario de prueba no ve los negocios del primero.

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
- [ ] Login y app funcionando contra Postgres, con el código actual (paso 3)
- [ ] Tú das el visto bueno para que publique la rama y abramos el PR (paso 4)
