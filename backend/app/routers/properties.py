"""CRUD de propiedades (solo staff). Se puede filtrar por client_id."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.supabase_client import get_service_client
from app.deps import require_staff
from app.models.schemas import CurrentUser, Property, PropertyCreate, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[Property])
def list_properties(
    client_id: UUID | None = Query(default=None),
    _: CurrentUser = Depends(require_staff),
) -> list[Property]:
    sb = get_service_client()
    query = sb.table("properties").select("*").order("created_at", desc=True)
    if client_id is not None:
        query = query.eq("client_id", str(client_id))
    res = query.execute()
    return [Property(**row) for row in res.data]


@router.post("", response_model=Property, status_code=status.HTTP_201_CREATED)
def create_property(
    body: PropertyCreate, _: CurrentUser = Depends(require_staff)
) -> Property:
    sb = get_service_client()
    res = sb.table("properties").insert(body.model_dump(mode="json")).execute()
    return Property(**res.data[0])


@router.get("/{property_id}", response_model=Property)
def get_property(
    property_id: UUID, _: CurrentUser = Depends(require_staff)
) -> Property:
    sb = get_service_client()
    res = (
        sb.table("properties").select("*").eq("id", str(property_id)).maybe_single().execute()
    )
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Propiedad no encontrada")
    return Property(**res.data)


@router.patch("/{property_id}", response_model=Property)
def update_property(
    property_id: UUID, body: PropertyUpdate, _: CurrentUser = Depends(require_staff)
) -> Property:
    sb = get_service_client()
    patch = body.model_dump(mode="json", exclude_unset=True)
    if not patch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nada que actualizar")
    res = sb.table("properties").update(patch).eq("id", str(property_id)).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Propiedad no encontrada")
    return Property(**res.data[0])


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: UUID, _: CurrentUser = Depends(require_staff)
) -> None:
    sb = get_service_client()
    sb.table("properties").delete().eq("id", str(property_id)).execute()
