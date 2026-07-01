"""Dependencias de FastAPI: resolución de identidad y control de acceso."""
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import decode_supabase_jwt
from app.core.supabase_client import get_service_client
from app.models.schemas import CurrentUser, StaffRole

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """Valida el JWT de Supabase y enriquece la identidad con staff/cliente.

    - Verifica firma y expiración del token.
    - Determina si el usuario es staff (tabla `staff`).
    - Resuelve los `client_id` asociados (tabla `app_users`).
    """
    payload = decode_supabase_jwt(credentials.credentials)
    user_id = UUID(payload["sub"])
    email = payload.get("email")

    sb = get_service_client()

    staff_row = (
        sb.table("staff")
        .select("role,is_active")
        .eq("id", str(user_id))
        .maybe_single()
        .execute()
    )
    is_staff = bool(staff_row.data and staff_row.data.get("is_active"))
    staff_role = (
        StaffRole(staff_row.data["role"]) if is_staff and staff_row.data else None
    )

    client_rows = (
        sb.table("app_users").select("client_id").eq("id", str(user_id)).execute()
    )
    client_ids = [UUID(r["client_id"]) for r in (client_rows.data or [])]

    return CurrentUser(
        user_id=user_id,
        email=email,
        is_staff=is_staff,
        staff_role=staff_role,
        client_ids=client_ids,
    )


def require_staff(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Exige que el usuario sea staff activo (técnico o admin)."""
    if not user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere permisos de técnico",
        )
    return user


def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Exige rol de administrador."""
    if user.staff_role != StaffRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere permisos de administrador",
        )
    return user


def verify_gateway_api_key(
    x_gateway_key: str = Header(..., alias="X-Gateway-Key"),
) -> None:
    """Autentica al Gateway Edge mediante una API key compartida."""
    settings = get_settings()
    if not settings.gateway_api_key or x_gateway_key != settings.gateway_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key de gateway inválida",
        )
