"""Cifrado simétrico de credenciales ONVIF mediante Fernet (AES-128-CBC + HMAC).

Las contraseñas ONVIF NUNCA se almacenan en claro. Solo el backend, que posee
la `FERNET_KEY`, puede descifrarlas en el momento de conectarse a la cámara.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.fernet_key.encode())


def encrypt_secret(plaintext: str) -> str:
    """Cifra un secreto y devuelve el token Fernet (str) para persistir en la BD."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Descifra un token Fernet. Lanza ValueError si el token es inválido."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # pragma: no cover - error de integridad/clave
        raise ValueError("Token de credencial inválido o clave incorrecta") from exc
