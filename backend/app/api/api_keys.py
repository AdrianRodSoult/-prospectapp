"""
Permite a cada cliente configurar sus propias API keys (Google Places,
Claude, GPT) desde la app, sin depender de que el operador (Adrián) las
configure en Render para todo el mundo. Se cifran antes de guardarse y
NUNCA se devuelven en texto plano, ni siquiera al propio dueño — solo se
informa de si están configuradas o no.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_secret
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, UserApiCredentials
from app.schemas.schemas import ApiCredentialsUpdate, ApiCredentialsStatus

router = APIRouter(prefix="/api/settings/api-keys", tags=["api-keys"])


def _get_or_create(db: Session, user_id: str) -> UserApiCredentials:
    row = db.query(UserApiCredentials).filter(UserApiCredentials.user_id == user_id).first()
    if not row:
        row = UserApiCredentials(user_id=user_id)
        db.add(row)
        db.flush()
    return row


@router.get("", response_model=ApiCredentialsStatus)
def get_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = db.query(UserApiCredentials).filter(UserApiCredentials.user_id == current_user.id).first()
    if not row:
        return ApiCredentialsStatus(
            google_places_configured=False, anthropic_configured=False, openai_configured=False,
        )
    return ApiCredentialsStatus(
        google_places_configured=bool(row.google_places_api_key_encrypted),
        anthropic_configured=bool(row.anthropic_api_key_encrypted),
        openai_configured=bool(row.openai_api_key_encrypted),
    )


@router.put("", response_model=ApiCredentialsStatus)
def update_keys(payload: ApiCredentialsUpdate, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    row = _get_or_create(db, current_user.id)

    # Solo se tocan los campos enviados. "" borra esa key concreta;
    # None (campo no enviado) la deja tal cual estaba.
    if payload.google_places_api_key is not None:
        row.google_places_api_key_encrypted = (
            encrypt_secret(payload.google_places_api_key) if payload.google_places_api_key else None
        )
    if payload.anthropic_api_key is not None:
        row.anthropic_api_key_encrypted = (
            encrypt_secret(payload.anthropic_api_key) if payload.anthropic_api_key else None
        )
    if payload.openai_api_key is not None:
        row.openai_api_key_encrypted = (
            encrypt_secret(payload.openai_api_key) if payload.openai_api_key else None
        )

    db.commit()
    db.refresh(row)
    return ApiCredentialsStatus(
        google_places_configured=bool(row.google_places_api_key_encrypted),
        anthropic_configured=bool(row.anthropic_api_key_encrypted),
        openai_configured=bool(row.openai_api_key_encrypted),
    )
