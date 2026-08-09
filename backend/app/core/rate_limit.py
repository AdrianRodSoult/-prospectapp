"""
Rate limiting por IP para endpoints sensibles (login, registro).

Usa almacenamiento en memoria (por proceso). Esto es correcto para el
despliegue actual (un único proceso uvicorn en Render, ver Dockerfile),
pero NO se comparte entre instancias si en el futuro se escala a más de
un worker/proceso. Si eso ocurre, cada proceso llevaría su propia cuenta
de intentos — el límite seguiría aplicándose, pero de forma menos
estricta (N instancias => hasta N veces el límite indicado). Migrar a
almacenamiento compartido (Redis) es la mejora natural de la Fase 5
(escalabilidad), no necesaria mientras solo haya un proceso.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
