"""CRUD de clientes (solo staff)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.supabase_client import get_service_client
from app.deps import require_staff
from app.models.schemas import Client, ClientCreate, ClientUpdate, CurrentUser

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[Client])
def list_clients(_: CurrentUser = Depends(require_staff)) -> list[Client]:
    sb = get_service_client()
    res = sb.table("clients").select("*").order("created_at", desc=True).execute()
    return [Client(**row) for row in res.data]


@router.post("", response_model=Client, status_code=status.HTTP_201_CREATED)
def create_client(
    body: ClientCreate, _: CurrentUser = Depends(require_staff)
) -> Client:
    sb = get_service_client()
    res = sb.table("clients").insert(body.model_dump(mode="json")).execute()
    return Client(**res.data[0])


@router.get("/{client_id}", response_model=Client)
def get_client(
    client_id: UUID, _: CurrentUser = Depends(require_staff)
) -> Client:
    sb = get_service_client()
    res = sb.table("clients").select("*").eq("id", str(client_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return Client(**res.data)


@router.patch("/{client_id}", response_model=Client)
def update_client(
    client_id: UUID, body: ClientUpdate, _: CurrentUser = Depends(require_staff)
) -> Client:
    sb = get_service_client()
    patch = body.model_dump(mode="json", exclude_unset=True)
    if not patch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nada que actualizar")
    res = sb.table("clients").update(patch).eq("id", str(client_id)).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return Client(**res.data[0])


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID, _: CurrentUser = Depends(require_staff)
) -> None:
    sb = get_service_client()
    sb.table("clients").delete().eq("id", str(client_id)).execute()
