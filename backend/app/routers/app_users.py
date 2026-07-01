"""Gestión de usuarios de la app móvil (solo staff).

Crea el usuario en Supabase Auth (admin API) y lo vincula a un cliente con su
rol en la tabla `app_users`.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.supabase_client import get_service_client
from app.deps import get_current_user, require_staff
from app.models.schemas import AppUser, AppUserCreate, AppUserInvite, CurrentUser

router = APIRouter(prefix="/app-users", tags=["app-users"])


def _create_linked_user(
    email: str, password: str, client_id: str, role: str
) -> AppUser:
    """Crea el usuario en Supabase Auth y lo vincula en `app_users`."""
    sb = get_service_client()
    try:
        created = sb.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No se pudo crear el usuario de auth: {exc}",
        ) from exc

    auth_user = created.user
    if auth_user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Auth no devolvió usuario")

    row = {
        "id": auth_user.id,
        "client_id": client_id,
        "email": email,
        "role": role,
    }
    try:
        res = sb.table("app_users").insert(row).execute()
    except Exception as exc:
        sb.auth.admin.delete_user(auth_user.id)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"No se pudo vincular el usuario: {exc}"
        ) from exc

    return AppUser(**res.data[0])


@router.get("", response_model=list[AppUser])
def list_app_users(
    client_id: UUID | None = Query(default=None),
    _: CurrentUser = Depends(require_staff),
) -> list[AppUser]:
    sb = get_service_client()
    query = sb.table("app_users").select("*").order("created_at", desc=True)
    if client_id is not None:
        query = query.eq("client_id", str(client_id))
    res = query.execute()
    return [AppUser(**row) for row in res.data]


@router.post("", response_model=AppUser, status_code=status.HTTP_201_CREATED)
def create_app_user(
    body: AppUserCreate, _: CurrentUser = Depends(require_staff)
) -> AppUser:
    return _create_linked_user(
        body.email, body.password, str(body.client_id), body.role.value
    )


@router.post(
    "/invite", response_model=AppUser, status_code=status.HTTP_201_CREATED
)
def invite_app_user(
    body: AppUserInvite, user: CurrentUser = Depends(get_current_user)
) -> AppUser:
    """Permite a un 'owner' invitar usuarios a SU cliente desde la app móvil.

    El solicitante debe ser staff o tener rol 'owner' sobre `client_id`.
    """
    if not user.is_staff:
        sb = get_service_client()
        owner = (
            sb.table("app_users")
            .select("role")
            .eq("id", str(user.user_id))
            .eq("client_id", str(body.client_id))
            .maybe_single()
            .execute()
        )
        if not owner.data or owner.data.get("role") != "owner":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Solo el 'owner' del cliente puede invitar usuarios",
            )
    return _create_linked_user(
        body.email, body.password, str(body.client_id), body.role.value
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_app_user(
    user_id: UUID, _: CurrentUser = Depends(require_staff)
) -> None:
    sb = get_service_client()
    # Borrar de auth (cascade elimina la fila de app_users por la FK).
    sb.auth.admin.delete_user(str(user_id))
