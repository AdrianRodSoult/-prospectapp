from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.rate_limit import limiter
from app.api import auth, profiles, search, export, gmail, compliance

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProspectApp API",
    description="Plataforma de prospección comercial local. Modo actual: "
                 f"Places={settings.PLACES_MODE}, IA={settings.AI_MODE}, Gmail={settings.GMAIL_MODE}",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://prospectapp-[a-zA-Z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Necesario para que el frontend pueda leer de qué fuente vinieron los
    # datos de una búsqueda (real / demo / real-con-fallback). Sin esto el
    # navegador oculta las cabeceras personalizadas aunque el backend las envíe.
    expose_headers=["X-Data-Source", "X-Data-Source-Warning"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(gmail.router)
app.include_router(compliance.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "places_mode": settings.PLACES_MODE,
        "ai_mode": settings.AI_MODE,
        "gmail_mode": settings.GMAIL_MODE,
    }
