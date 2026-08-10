"""
Helper centralizado: obtiene las API keys propias de un usuario (si las
configuró), ya descifradas, listas para pasar a los proveedores.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.models.models import UserApiCredentials


@dataclass
class UserCredentials:
    google_places_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None


def get_user_credentials(db: Session, user_id: str) -> UserCredentials:
    row = db.query(UserApiCredentials).filter(UserApiCredentials.user_id == user_id).first()
    if not row:
        return UserCredentials()
    return UserCredentials(
        google_places_api_key=decrypt_secret(row.google_places_api_key_encrypted)
        if row.google_places_api_key_encrypted else None,
        anthropic_api_key=decrypt_secret(row.anthropic_api_key_encrypted)
        if row.anthropic_api_key_encrypted else None,
        openai_api_key=decrypt_secret(row.openai_api_key_encrypted)
        if row.openai_api_key_encrypted else None,
    )
