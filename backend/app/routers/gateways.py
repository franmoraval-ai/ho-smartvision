"""CRUD de gateways Edge (solo staff)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.supabase_client import get_service_client
from app.deps import require_staff, verify_gateway_api_key
from app.models.schemas import (
    Camera,
    CurrentUser,
    Gateway,
    GatewayCreate,
    GatewayHeartbeat,
)

router = APIRouter(prefix="/gateways", tags=["gateways"])


@router.get("", response_model=list[Gateway])
def list_gateways(
    property_id: UUID | None = Query(default=None),
    _: CurrentUser = Depends(require_staff),
) -> list[Gateway]:
    sb = get_service_client()
    query = sb.table("gateways").select("*").order("created_at", desc=True)
    if property_id is not None:
        query = query.eq("property_id", str(property_id))
    res = query.execute()
    return [Gateway(**row) for row in res.data]


@router.post("", response_model=Gateway, status_code=status.HTTP_201_CREATED)
def create_gateway(
    body: GatewayCreate, _: CurrentUser = Depends(require_staff)
) -> Gateway:
    sb = get_service_client()
    res = sb.table("gateways").insert(body.model_dump(mode="json")).execute()
    return Gateway(**res.data[0])


@router.delete("/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gateway(
    gateway_id: UUID, _: CurrentUser = Depends(require_staff)
) -> None:
    sb = get_service_client()
    sb.table("gateways").delete().eq("id", str(gateway_id)).execute()


@router.post(
    "/heartbeat",
    response_model=Gateway,
    dependencies=[Depends(verify_gateway_api_key)],
)
def gateway_heartbeat(body: GatewayHeartbeat) -> Gateway:
    """Latido del Gateway Edge: actualiza `last_seen` por `device_id`.

    Header requerido: `X-Gateway-Key: <GATEWAY_API_KEY>`.
    """
    sb = get_service_client()
    now = datetime.now(timezone.utc).isoformat()
    res = (
        sb.table("gateways")
        .update({"last_seen": now})
        .eq("device_id", body.device_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gateway no registrado (device_id desconocido)",
        )
    return Gateway(**res.data[0])


@router.get(
    "/cameras",
    response_model=list[Camera],
    dependencies=[Depends(verify_gateway_api_key)],
)
def gateway_cameras(device_id: str = Query(..., min_length=1)) -> list[Camera]:
    """Cámaras asignadas a este gateway (para mapear ONVIF IP → camera_id).

    Header requerido: `X-Gateway-Key: <GATEWAY_API_KEY>`. No expone credenciales.
    """
    sb = get_service_client()
    gw = (
        sb.table("gateways")
        .select("id")
        .eq("device_id", device_id)
        .maybe_single()
        .execute()
    )
    if not gw.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gateway no registrado (device_id desconocido)",
        )
    rows = (
        sb.table("cameras")
        .select("*")
        .eq("gateway_id", gw.data["id"])
        .execute()
    )
    return [Camera(**row) for row in rows.data]
