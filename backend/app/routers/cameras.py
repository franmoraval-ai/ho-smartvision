"""CRUD de cámaras (solo staff).

La contraseña ONVIF llega en claro, se cifra con Fernet antes de persistir y
NUNCA se devuelve en las respuestas.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.crypto import encrypt_secret
from app.core.supabase_client import get_service_client
from app.deps import require_staff
from app.models.schemas import Camera, CameraCreate, CameraUpdate, CurrentUser

router = APIRouter(prefix="/cameras", tags=["cameras"])

# Columnas seguras a devolver (sin onvif_password_encrypted).
_SAFE_COLUMNS = (
    "id,property_id,gateway_id,name,rtsp_url,onvif_ip,onvif_username,is_active,created_at"
)


@router.get("", response_model=list[Camera])
def list_cameras(
    property_id: UUID | None = Query(default=None),
    _: CurrentUser = Depends(require_staff),
) -> list[Camera]:
    sb = get_service_client()
    query = sb.table("cameras").select(_SAFE_COLUMNS).order("created_at", desc=True)
    if property_id is not None:
        query = query.eq("property_id", str(property_id))
    res = query.execute()
    return [Camera(**row) for row in res.data]


@router.post("", response_model=Camera, status_code=status.HTTP_201_CREATED)
def create_camera(
    body: CameraCreate, _: CurrentUser = Depends(require_staff)
) -> Camera:
    payload: dict[str, Any] = body.model_dump(mode="json", exclude={"onvif_password"})
    if body.onvif_password:
        payload["onvif_password_encrypted"] = encrypt_secret(body.onvif_password)

    sb = get_service_client()
    res = sb.table("cameras").insert(payload).execute()
    created = sb.table("cameras").select(_SAFE_COLUMNS).eq("id", res.data[0]["id"]).single().execute()
    return Camera(**created.data)


@router.get("/{camera_id}", response_model=Camera)
def get_camera(
    camera_id: UUID, _: CurrentUser = Depends(require_staff)
) -> Camera:
    sb = get_service_client()
    res = sb.table("cameras").select(_SAFE_COLUMNS).eq("id", str(camera_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")
    return Camera(**res.data)


@router.patch("/{camera_id}", response_model=Camera)
def update_camera(
    camera_id: UUID, body: CameraUpdate, _: CurrentUser = Depends(require_staff)
) -> Camera:
    patch: dict[str, Any] = body.model_dump(mode="json", exclude_unset=True, exclude={"onvif_password"})
    if body.onvif_password is not None:
        patch["onvif_password_encrypted"] = encrypt_secret(body.onvif_password)
    if not patch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nada que actualizar")

    sb = get_service_client()
    res = sb.table("cameras").update(patch).eq("id", str(camera_id)).execute()
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")
    updated = sb.table("cameras").select(_SAFE_COLUMNS).eq("id", str(camera_id)).single().execute()
    return Camera(**updated.data)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(
    camera_id: UUID, _: CurrentUser = Depends(require_staff)
) -> None:
    sb = get_service_client()
    sb.table("cameras").delete().eq("id", str(camera_id)).execute()
