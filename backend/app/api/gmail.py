"""
Integración Gmail. En modo mock (sin credenciales OAuth configuradas),
simula la creación de borradores para poder probar todo el flujo gratis.
En modo live, usa OAuth 2.0 con alcance mínimo (gmail.compose).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import EmailConnection, MessageDraft, Business, User, Activity
from app.services.organizations import get_teammate_user_ids

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
settings = get_settings()


@router.get("/status")
def status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conn = db.query(EmailConnection).filter(
        EmailConnection.user_id == current_user.id, EmailConnection.revoked == False  # noqa: E712
    ).first()
    return {
        "mode": settings.GMAIL_MODE,
        "connected": conn is not None,
        "email_address": conn.email_address if conn else None,
    }


@router.post("/connect")
def connect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    En modo live, esto debería redirigir al flujo OAuth de Google.
    Aquí devolvemos la URL de autorización a construir en el frontend,
    o simulamos la conexión si no hay credenciales (modo demo).
    """
    if settings.GMAIL_MODE == "live":
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.GOOGLE_OAUTH_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_OAUTH_REDIRECT_URI}"
            "&response_type=code&scope=https://www.googleapis.com/auth/gmail.compose"
            "&access_type=offline&prompt=consent"
        )
        return {"mode": "live", "auth_url": auth_url}

    conn = EmailConnection(
        user_id=current_user.id, email_address=f"{current_user.email}",
        provider="gmail", mode="mock",
    )
    db.add(conn)
    db.commit()
    return {"mode": "mock", "connected": True, "email_address": conn.email_address}


@router.post("/disconnect")
def disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(EmailConnection).filter(EmailConnection.user_id == current_user.id).update({"revoked": True})
    db.commit()
    return {"ok": True}


@router.post("/drafts/{message_draft_id}")
def create_draft(message_draft_id: str, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    teammate_ids = get_teammate_user_ids(db, current_user.id)
    draft = (
        db.query(MessageDraft)
        .join(Business, Business.id == MessageDraft.business_id)
        .filter(MessageDraft.id == message_draft_id, Business.owner_user_id.in_(teammate_ids))
        .first()
    )
    if not draft:
        raise HTTPException(404, "Borrador de mensaje no encontrado")
    conn = db.query(EmailConnection).filter(
        EmailConnection.user_id == current_user.id, EmailConnection.revoked == False  # noqa: E712
    ).first()
    if not conn:
        raise HTTPException(400, "Conecta Gmail antes de crear un borrador")

    if conn.mode == "mock":
        draft.gmail_draft_id = f"mock-draft-{uuid.uuid4().hex[:8]}"
    else:
        # TODO Fase 2: llamada real a Gmail API (users.drafts.create) con el token OAuth almacenado.
        raise HTTPException(501, "Integración Gmail en vivo pendiente de credenciales verificadas")

    draft.status = "draft"
    db.add(Activity(business_id=draft.business_id, type="gmail_draft_created",
                     description="Borrador creado en Gmail (mock)" if conn.mode == "mock" else "Borrador creado"))
    db.commit()
    return {"gmail_draft_id": draft.gmail_draft_id, "mode": conn.mode}
