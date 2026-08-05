# Despliegue: PostgreSQL persistente + aislamiento multi-tenant en Render

Esta guía cubre exactamente los pasos manuales que **tienes que hacer tú**
en el panel de Render para esta rama. El código ya está listo y probado;
esto es solo configuración de infraestructura, imprescindible para que
funcione (no hay forma de evitarlo).

## 1. Crear la base de datos Postgres en Render

1. Panel de Render → **New** → **PostgreSQL**.
2. Nombre sugerido: `prospectapp-db`. Plan: el gratuito sirve para validar
   esta migración (revisa sus límites de almacenamiento antes de tener
   clientes reales; el free tier de Render Postgres además expira a los
   90 días si no lo actualizas a un plan de pago).
3. Región: la misma que tu backend, para latencia mínima.
4. Una vez creada, copia el valor **"Internal Database URL"** (no el
   "External"): tiene el formato
   `postgres://usuario:password@host-interno/nombre_bd`.

## 2. Configurar el backend (servicio web en Render)

En el servicio del backend → **Environment**, añade/edita:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | La *Internal Database URL* copiada en el paso 1 (el código ya normaliza `postgres://` a `postgresql://` automáticamente, no hace falta que la edites a mano) |
| `SECRET_KEY` | Una clave larga y aleatoria — **no dejes el valor por defecto del código en producción** |

El resto de variables (`AI_PROVIDER`, `GOOGLE_PLACES_API_KEY`, etc.) siguen
igual que ya las tenías.

## 3. Migraciones automáticas en cada despliegue

Ya está resuelto en el `Dockerfile` de esta rama: el contenedor ejecuta
`alembic upgrade head` automáticamente antes de arrancar el servidor, en
cada despliegue. **No tienes que ejecutar nada a mano.**

Si tu servicio en Render **no** usa el Dockerfile (por ejemplo, si lo
configuraste como "Native Python Environment" con un *Start Command*
manual en el panel), entonces edita ahí el *Start Command* a:

```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

(nota el `$PORT` en vez de `8000` fijo — Render asigna el puerto por
variable de entorno en ese modo).

## 4. Qué va a pasar con tus datos actuales

Tienes un usuario real ya creado. Al desplegar esta rama:

- El usuario **no se toca ni se borra** — la migración solo añade una
  columna nueva a la tabla `businesses`.
- Si ya guardaste algún negocio de prueba con ese usuario, la migración
  le asignará automáticamente ese usuario como propietario (lo probé con
  datos que simulan tu caso exacto).
- Si hubiera algún negocio sin búsqueda asociada (no debería, pero por si
  acaso), se eliminaría junto con sus datos dependientes — ya confirmaste
  que no hay nada comercial importante que conservar.

**Recomendación de todas formas:** antes de desplegar esta rama, haz una
copia de seguridad rápida desde Render (Backups del propio Postgres, o
`pg_dump` si aún estás en SQLite y quieres exportar antes de cambiar).

## 5. Verificación después de desplegar

1. Entra a la app y confirma que tu login sigue funcionando.
2. Haz una búsqueda nueva y comprueba que aparece en `/results`.
3. (Opcional, para verificar el aislamiento) Registra un segundo usuario
   de prueba, haz una búsqueda con el mismo nicho/ciudad, y confirma que
   no ve los negocios del primer usuario.

## 6. Rollback si algo sale mal

Como el `Dockerfile` corre `alembic upgrade head` automáticamente, revertir
significa desplegar de nuevo la versión anterior de la imagen (Render
guarda despliegues previos: **Manual Deploy → Redeploy** sobre el commit
anterior a este merge). La migración en sí también tiene un `downgrade()`
funcional por si necesitas revertir el esquema manualmente:

```
alembic downgrade -1
```
