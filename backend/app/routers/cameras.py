"""CRUD de cámaras y resolución del stream en vivo.

- Las credenciales sensibles (contraseña ONVIF/local y código de verificación
  del cloud) llegan en claro, se cifran con Fernet antes de persistir y NUNCA se
  devuelven en las respuestas.
- `GET /cameras/{id}/stream` resuelve una URL de reproducción en vivo usando el
  cloud del fabricante (Ezviz/Imou) o el acceso directo (Reolink/Tapo).
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.supabase_client import get_service_client
from app.deps import get_current_user, require_staff
from app.models.schemas import (
    Camera,
    CameraCreate,
    CameraProvider,
    CameraStream,
    CameraUpdate,
    CurrentUser,
    ProviderDeviceOut,
    ProviderInfo,
)
from app.providers import (
    CameraCredentials,
    ProviderError,
    ProviderNotConfigured,
    get_provider,
)
from app.providers.registry import all_providers

router = APIRouter(prefix="/cameras", tags=["cameras"])

# Columnas seguras a devolver (sin secretos cifrados).
_SAFE_COLUMNS = (
    "id,property_id,gateway_id,name,rtsp_url,onvif_ip,onvif_username,is_active,"
    "provider,provider_device_serial,provider_channel,created_at"
)


def _encrypt_secrets(payload: dict[str, Any], body: CameraCreate | CameraUpdate) -> None:
    """Cifra en el payload los secretos entrantes (contraseña / código)."""
    if getattr(body, "onvif_password", None):
        payload["onvif_password_encrypted"] = encrypt_secret(body.onvif_password)
    if getattr(body, "provider_verify_code", None):
        payload["provider_verify_code_encrypted"] = encrypt_secret(
            body.provider_verify_code
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
    payload: dict[str, Any] = body.model_dump(
        mode="json", exclude={"onvif_password", "provider_verify_code"}
    )
    _encrypt_secrets(payload, body)

    sb = get_service_client()
    res = sb.table("cameras").insert(payload).execute()
    created = sb.table("cameras").select(_SAFE_COLUMNS).eq("id", res.data[0]["id"]).single().execute()
    return Camera(**created.data)


# ---------------------------------------------------------------------------
# Proveedores de streaming (metadatos y descubrimiento por cuenta)
# Declarados ANTES de "/{camera_id}" para que no los eclipse el path param UUID.
# ---------------------------------------------------------------------------
@router.get("/providers", response_model=list[ProviderInfo])
def list_providers(_: CurrentUser = Depends(require_staff)) -> list[ProviderInfo]:
    """Lista los proveedores soportados y si están configurados."""
    return [
        ProviderInfo(name=p.name, cloud=p.cloud, configured=p.is_configured())
        for p in all_providers()
    ]


@router.get(
    "/providers/{provider_name}/devices",
    response_model=list[ProviderDeviceOut],
)
def list_provider_devices(
    provider_name: str, _: CurrentUser = Depends(require_staff)
) -> list[ProviderDeviceOut]:
    """Descubre las cámaras vinculadas a la cuenta de operador del proveedor.

    Útil para dar de alta cámaras sin teclear el número de serie a mano.
    Solo aplica a proveedores cloud (ezviz/imou).
    """
    provider = get_provider(provider_name)
    try:
        devices = provider.list_devices()
    except ProviderNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return [
        ProviderDeviceOut(
            serial=d.serial,
            name=d.name,
            online=d.online,
            channels=d.channels,
            model=d.model,
        )
        for d in devices
    ]


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
    patch: dict[str, Any] = body.model_dump(
        mode="json", exclude_unset=True, exclude={"onvif_password", "provider_verify_code"}
    )
    _encrypt_secrets(patch, body)
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


# ---------------------------------------------------------------------------
# Stream en vivo (accesible por staff y por los usuarios del cliente dueño)
# ---------------------------------------------------------------------------
def _assert_camera_access(camera_row: dict[str, Any], user: CurrentUser) -> None:
    """Autoriza a staff o a un usuario del cliente propietario de la cámara."""
    if user.is_staff:
        return
    sb = get_service_client()
    prop = (
        sb.table("properties")
        .select("client_id")
        .eq("id", camera_row["property_id"])
        .maybe_single()
        .execute()
    )
    client_id = prop.data.get("client_id") if prop.data else None
    if not client_id or UUID(client_id) not in user.client_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso a esta cámara")


def _credentials_from_row(row: dict[str, Any]) -> CameraCredentials:
    """Construye las credenciales (descifrando secretos) según el proveedor."""
    provider = row.get("provider") or CameraProvider.local.value
    verify_code = None
    if row.get("provider_verify_code_encrypted"):
        verify_code = decrypt_secret(row["provider_verify_code_encrypted"])

    if provider in (CameraProvider.reolink.value, CameraProvider.tapo.value):
        password = None
        if row.get("onvif_password_encrypted"):
            password = decrypt_secret(row["onvif_password_encrypted"])
        return CameraCredentials(
            channel=row.get("provider_channel") or 1,
            host=str(row["onvif_ip"]) if row.get("onvif_ip") else None,
            username=row.get("onvif_username"),
            password=password,
        )
    # Cloud (ezviz/imou)
    return CameraCredentials(
        device_serial=row.get("provider_device_serial"),
        channel=row.get("provider_channel") or 1,
        verify_code=verify_code,
    )


@router.get("/{camera_id}/stream", response_model=CameraStream)
def get_camera_stream(
    camera_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> CameraStream:
    sb = get_service_client()
    row = (
        sb.table("cameras")
        .select(
            "id,property_id,provider,provider_device_serial,provider_channel,"
            "provider_verify_code_encrypted,onvif_ip,onvif_username,"
            "onvif_password_encrypted,is_active"
        )
        .eq("id", str(camera_id))
        .maybe_single()
        .execute()
    )
    if not row.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")

    _assert_camera_access(row.data, user)

    provider_name = row.data.get("provider") or CameraProvider.local.value
    if provider_name == CameraProvider.local.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cámara local: usa el visor del gateway (go2rtc).",
        )

    provider = get_provider(provider_name)
    creds = _credentials_from_row(row.data)
    try:
        info = provider.get_live_stream(creds)
    except ProviderNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    browser_playable = info.protocol.browser_playable and info.url.startswith("https")
    return CameraStream(
        camera_id=camera_id,
        provider=CameraProvider(provider_name),
        url=info.url,
        protocol=info.protocol.value,
        cloud=provider.cloud,
        browser_playable=browser_playable,
        expires_at=info.expires_at,
    )
