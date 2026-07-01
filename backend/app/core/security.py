"""Verificación de JWT emitidos por Supabase Auth.

Soporta dos esquemas:
- **HS256** con el JWT secret compartido (legacy).
- **RS256/ES256** con las "JWT Signing Keys" asimétricas (proyectos nuevos),
  validadas contra el endpoint JWKS público del proyecto.
"""
from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.core.config import get_settings

_ASYMMETRIC_ALGS = ["RS256", "ES256", "RS384", "ES384", "RS512", "ES512"]


@lru_cache
def _jwks_client() -> PyJWKClient:
    """Cliente JWKS cacheado apuntando al proyecto Supabase."""
    settings = get_settings()
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """Valida y decodifica un JWT de Supabase.

    Detecta el algoritmo en la cabecera del token: HS256 usa el secreto
    compartido; los algoritmos asimétricos se validan vía JWKS.
    Devuelve el payload (claims) si es válido; en caso contrario lanza 401.
    """
    settings = get_settings()
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
        common = dict(
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
        if alg in _ASYMMETRIC_ALGS:
            signing_key = _jwks_client().get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token, signing_key, algorithms=_ASYMMETRIC_ALGS, **common
            )
        elif alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token HS256 recibido pero SUPABASE_JWT_SECRET no está configurado",
                )
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                **common,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Algoritmo de token no soportado: {alg}",
            )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from exc
    return payload
