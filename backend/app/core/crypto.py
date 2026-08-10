"""
Cifrado simétrico (Fernet) para las API keys que cada cliente introduce
desde la app (Google Places, Claude, GPT). Nunca se guardan en texto plano.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.CREDENTIALS_ENCRYPTION_KEY.encode())


def encrypt_secret(plain_value: str) -> str:
    return _get_fernet().encrypt(plain_value.encode()).decode()


def decrypt_secret(encrypted_value: str) -> str | None:
    """
    Devuelve None (en vez de lanzar una excepción) si el valor no se puede
    descifrar — por ejemplo, si CREDENTIALS_ENCRYPTION_KEY cambió. Preferible
    a que una key ilegible tumbe la petición del usuario: simplemente se
    trata como si no hubiera key propia configurada (cae al modo demo).
    """
    try:
        return _get_fernet().decrypt(encrypted_value.encode()).decode()
    except (InvalidToken, ValueError):
        return None
