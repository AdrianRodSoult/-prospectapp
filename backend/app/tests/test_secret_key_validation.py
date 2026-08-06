"""
Verifica que un SECRET_KEY débil o por defecto bloquea el arranque en
producción, pero nunca en desarrollo/tests (para no romper el flujo local).
"""
import pytest

from app.core.config import (
    validate_secret_key, INSECURE_DEFAULT_SECRET_KEY, MIN_SECRET_KEY_LENGTH,
)


def test_default_key_blocked_in_production():
    with pytest.raises(RuntimeError, match="valor por defecto inseguro"):
        validate_secret_key(INSECURE_DEFAULT_SECRET_KEY, is_production=True)


def test_short_key_blocked_in_production():
    with pytest.raises(RuntimeError, match="demasiado corto"):
        validate_secret_key("una-clave-corta", is_production=True)


def test_strong_key_allowed_in_production():
    strong_key = "x" * MIN_SECRET_KEY_LENGTH
    validate_secret_key(strong_key, is_production=True)  # no debe lanzar nada


def test_default_key_allowed_outside_production():
    # En desarrollo/tests no debe bloquear nada, aunque la clave sea la de por defecto.
    validate_secret_key(INSECURE_DEFAULT_SECRET_KEY, is_production=False)
