# ProspectApp — Plataforma de prospección comercial local (MVP · Fase 1)

Encuentra negocios locales que podrían necesitar una web nueva o mejorar su
presencia digital: descubrimiento, auditoría web, detección de oportunidades,
puntuación explicable, mensajes generados por IA y un CRM ligero.

**Funciona gratis desde el primer minuto**, en **modo demostración** (datos
ficticios generados localmente, sin llamar a ninguna API de pago). Puedes
conectar Google Places, Claude/GPT y Gmail más adelante, cuando quieras usar
datos reales, sin cambiar una línea de código — solo variables de entorno.

**Se usa desde el navegador**: funciona perfectamente en Safari en iPad y en
el móvil (diseño responsive, navegación pensada para el pulgar). No es una
app nativa de iPadOS; es una web app que abres desde Safari.

---

## 1. Arquitectura

- **Backend**: FastAPI + SQLAlchemy + SQLite (por defecto) o PostgreSQL.
- **Frontend**: Next.js + TypeScript + Tailwind, responsive mobile-first.
- **Proveedores intercambiables** (`BusinessDataProvider`, `AIProvider`):
  cada uno declara fuente, confianza, coste y limitaciones. Sin credenciales,
  se usa automáticamente un proveedor **mock** que nunca se presenta como dato real.

```
prospectapp/
├── backend/        FastAPI, modelos, proveedores, motor de puntuación/oportunidades
├── frontend/        Next.js (páginas: login, onboarding, búsqueda, resultados, CRM…)
├── docker-compose.yml
└── .env.example
```

## 2. Arrancar en local (gratis, con Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8000/docs (documentación interactiva)
- Frontend: http://localhost:3000

Desde el iPad/móvil, en la misma red Wi-Fi, sustituye `localhost` por la IP
de tu ordenador (ej. `http://192.168.1.20:3000`) y ajusta `NEXT_PUBLIC_API_URL`
en `docker-compose.yml` a esa misma IP con el puerto 8000.

Para publicarlo en internet gratis, puedes desplegar el backend en el free
tier de Render/Railway/Fly.io y el frontend en Vercel (plan gratuito) o
Netlify — así lo abres desde Safari en cualquier sitio sin instalar nada.

## 3. Arrancar sin Docker (desarrollo)

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

## 4. Modo demo vs. modo real

| Componente     | Sin credenciales (por defecto) | Con credenciales |
|-----------------|-------------------------------|-------------------|
| Búsqueda        | Datos ficticios locales, gratis | Google Places API (de pago) |
| Auditoría web   | Simulada de forma determinista | Crawler real (gratis, respeta robots.txt) |
| Generación de mensajes | Plantillas locales | Claude o GPT (de pago) |
| Gmail           | Borrador simulado | OAuth real + borradores reales |

La interfaz nunca oculta esto: cada dato muestra su fuente y su nivel de
confianza (verificado / encontrado / inferido / no verificado).

## 5. Configurar APIs reales (opcional)

### Google Places API
1. Crea un proyecto en Google Cloud Console y activa "Places API (New)".
2. Genera una API key y restríngela por IP o referrer.
3. Añade `GOOGLE_PLACES_API_KEY=...` en `.env`.
4. Google ofrece crédito mensual gratuito; revisa los precios actuales antes de usarlo a gran escala.

### Claude (Anthropic)
1. Crea una API key en https://console.anthropic.com
2. En `.env`: `AI_PROVIDER=anthropic` y `ANTHROPIC_API_KEY=...`

### OpenAI (GPT)
1. Crea una API key en https://platform.openai.com
2. En `.env`: `AI_PROVIDER=openai` y `OPENAI_API_KEY=...`

### Gmail OAuth
1. Crea credenciales OAuth 2.0 (tipo "Web application") en Google Cloud Console.
2. Alcance mínimo necesario: `https://www.googleapis.com/auth/gmail.compose`
3. Añade `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`.
4. La Fase 1 solo crea borradores (nunca envía automáticamente).

## 6. Tests

```bash
cd backend
python -m pytest app/tests -v
```

Los tests cubren: registro/login, flujo completo (perfil → búsqueda →
auditoría → puntuación → mensaje → CRM → exportación) y deduplicación por
`place_id`. Todo con datos ficticios, nunca negocios reales.

## 7. Limitaciones reales de esta Fase 1

- No incluye envío real de emails/WhatsApp (solo borradores) — así se evita
  cualquier envío accidental antes de que lo revises.
- No incluye mapa interactivo (requeriría una clave de Google Maps de pago);
  los resultados se muestran en tarjetas y tabla.
- No incluye PageSpeed Insights, capturas visuales con IA, WhatsApp Business
  API ni campañas — están planificadas para Fase 2/3 (ver `FUTURE_WORK.md`).
- El auditor web en modo "live" solo visita páginas públicas del propio
  dominio y respeta límites de tiempo/tamaño; sitios con fuerte protección
  antibot pueden no ser auditables (por diseño, no se intenta evadir eso).
- El detector de "encaje con el cliente ideal" es una heurística simple en
  esta fase; se puede sustituir por una más sofisticada sin tocar el resto.

## 8. Cumplimiento y uso responsable

- Nunca se envía nada sin confirmación humana explícita.
- Existe lista de exclusión (`suppression_entries`) y penalización fuerte
  en el score para negocios excluidos o ya rechazados.
- Todo dato indica su fuente y confianza; nunca se afirma algo no verificado.
- **Este software no sustituye asesoría legal.** Antes de contactar negocios
  reales, revisa la normativa de protección de datos y comunicaciones
  comerciales aplicable en tu país (en la UE: RGPD y LSSI-CE, entre otras).

## 9. Checklist de seguridad incluida

- [x] Contraseñas con bcrypt, sesiones con JWT
- [x] Crawler bloquea localhost, IPs privadas y metadata cloud (SSRF)
- [x] Solo esquemas http/https permitidos en el crawler
- [x] Límite de tamaño y tiempo por página rastreada
- [x] Claves de API solo en variables de entorno, nunca en el navegador
- [x] CORS restringido por configuración
- [x] Todo el contenido extraído de webs se trata como no confiable frente a la IA

## 10. Próximas tareas (ver FUTURE_WORK.md)

Fase 2: envío real por Gmail, seguimientos automáticos con guardas, PageSpeed
Insights, análisis visual con IA, analítica comercial avanzada.
Fase 3: WhatsApp Business API, campañas, redes sociales, roles y multiusuario,
aprendizaje basado en resultados reales.
