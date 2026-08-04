from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.api import auth, profiles, search, export, gmail, compliance

settings = get_settings()
print("CORS:",settings.CORS_ORIGINS)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProspectApp API",
    description="Plataforma de prospección comercial local. Modo actual: "
                 f"Places={settings.PLACES_MODE}, IA={settings.AI_MODE}, Gmail={settings.GMAIL_MODE}",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
