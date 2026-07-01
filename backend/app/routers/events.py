"""Eventos: ingestión desde el Gateway Edge y consulta desde el panel."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.supabase_client import get_service_client
from app.deps import require_staff, verify_gateway_api_key
from app.models.schemas import CurrentUser, Event, EventCreate

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[Event])
def list_events(
    camera_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _: CurrentUser = Depends(require_staff),
) -> list[Event]:
    """Lista eventos recientes (panel de técnicos)."""
    sb = get_service_client()
    query = sb.table("events").select("*").order("timestamp", desc=True).limit(limit)
    if camera_id is not None:
        query = query.eq("camera_id", str(camera_id))
    res = query.execute()
    return [Event(**row) for row in res.data]


@router.post(
    "/ingest",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_gateway_api_key)],
)
def ingest_event(body: EventCreate) -> Event:
    """Webhook de ingestión usado por el Gateway Edge (autenticado por API key).

    Header requerido: `X-Gateway-Key: <GATEWAY_API_KEY>`.
    """
    sb = get_service_client()
    res = sb.table("events").insert(body.model_dump(mode="json")).execute()
    return Event(**res.data[0])
