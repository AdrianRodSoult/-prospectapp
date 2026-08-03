# Tareas futuras

## Fase 2
- [ ] Envío real de emails vía Gmail API (`users.messages.send`) tras confirmación,
      con límites diarios configurables y detección de respuestas por hilo.
- [ ] Seguimientos automáticos con guardas (comprobar exclusión, respuesta previa,
      estado y límites antes de cada envío; parar ante cualquier respuesta).
- [ ] Integración PageSpeed Insights / Lighthouse para rendimiento real
      (Core Web Vitals, tiempos de carga móvil/escritorio).
- [ ] Captura de pantalla + análisis visual con IA, etiquetado siempre como
      "evaluación estimada", nunca como hecho objetivo.
- [ ] Analítica comercial: qué nichos, ciudades, canales y mensajes generan
      más respuestas (estadística simple primero, sin ML opaco).
- [ ] Control de costes avanzado: caché de auditorías recientes, reutilización,
      límites mensuales duros por usuario/organización.
- [ ] Colas en segundo plano (Celery/Dramatiq) para búsquedas y auditorías
      grandes, con estado, progreso y cancelación.

## Fase 3
- [ ] WhatsApp Business Platform (API oficial): plantillas aprobadas, webhooks,
      estados de entrega, parada automática al responder.
- [ ] Campañas multi-negocio con miembros de campaña y métricas agregadas.
- [ ] Análisis de redes sociales vía APIs oficiales (sin inventar seguidores,
      engagement ni fechas de actividad no verificables).
- [ ] Roles y multiusuario por organización (separación de datos, permisos).
- [ ] Aprendizaje basado en resultados: ajuste sugerido de pesos del scoring
      a partir de datos reales, siempre mostrando el cambio propuesto antes
      de aplicarlo (nunca automático y silencioso).
- [ ] Módulo `SocialPresenceAnalyzer` completo.
- [ ] Mapa interactivo con Google Maps JavaScript API (requiere key de pago;
      por eso se dejó fuera del MVP gratuito).

## Deuda técnica conocida
- Sustituir `datetime.utcnow()` (deprecado) por `datetime.now(timezone.utc)`
  en todo el backend.
- Añadir Alembic con migraciones versionadas (ahora se usa `create_all`,
  válido para el MVP pero no para producción con datos reales).
- Añadir rate limiting real (por IP/usuario) en endpoints públicos.
- Tests end-to-end de frontend (Playwright) además de los tests de backend.
