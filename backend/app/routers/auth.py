"""Rutas de autenticación: login con Supabase y consulta de identidad."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase_client import get_anon_client
from app.deps import get_current_user
from app.models.schemas import CurrentUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """Inicia sesión con email/contraseña contra Supabase Auth.

    Devuelve el access_token (JWT) y el refresh_token. El panel web debe enviar
    el access_token como `Authorization: Bearer <token>` en cada petición.
    """
    sb = get_anon_client()
    try:
        result = sb.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:  # supabase lanza AuthApiError genérico
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        ) from exc

    session = result.session
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in or 3600,
    )


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Devuelve la identidad resuelta del usuario autenticado."""
    return user
