"""Descubrimiento ONVIF en la red local.

Intenta un descubrimiento real vía WS-Discovery. Si las librerías no están
disponibles o falla (entorno cloud sin acceso a la LAN), degrada a modo
**simulado** devolviendo dispositivos de ejemplo para poder desarrollar la UI.

NOTA: el descubrimiento real solo funciona cuando el backend corre en la MISMA
red local que las cámaras (p. ej. en el Gateway Edge). En producción cloud,
el Gateway debe ejecutar el descubrimiento y llamar a este backend.
"""
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Query

from app.deps import require_staff
from app.models.schemas import CurrentUser, OnvifDevice, OnvifDiscoveryResponse

router = APIRouter(prefix="/discover-onvif", tags=["onvif"])


def _simulated_devices() -> list[OnvifDevice]:
    """Dispositivos de ejemplo para desarrollo / demo de la UI."""
    return [
        OnvifDevice(
            ip="192.168.1.50",
            port=80,
            name="Cámara entrada (demo)",
            manufacturer="Hikvision",
            model="DS-2CD2042",
            xaddrs=["http://192.168.1.50/onvif/device_service"],
            rtsp_hint="rtsp://192.168.1.50:554/Streaming/Channels/101",
        ),
        OnvifDevice(
            ip="192.168.1.51",
            port=80,
            name="Cámara patio (demo)",
            manufacturer="Dahua",
            model="IPC-HFW1230S",
            xaddrs=["http://192.168.1.51/onvif/device_service"],
            rtsp_hint="rtsp://192.168.1.51:554/cam/realmonitor?channel=1&subtype=0",
        ),
    ]


def _real_discovery(timeout: int) -> list[OnvifDevice]:
    """Descubrimiento real vía WS-Discovery. Lanza si la librería no existe."""
    from wsdiscovery.discovery import ThreadedWSDiscovery  # type: ignore

    wsd = ThreadedWSDiscovery()
    devices: list[OnvifDevice] = []
    try:
        wsd.start()
        services = wsd.searchServices(timeout=timeout)
        for svc in services:
            xaddrs = list(svc.getXAddrs())
            host = None
            port = 80
            if xaddrs:
                parsed = urlparse(xaddrs[0])
                host = parsed.hostname
                port = parsed.port or 80
            if not host:
                continue
            scopes = " ".join(str(s) for s in svc.getScopes())
            devices.append(
                OnvifDevice(
                    ip=host,
                    port=port,
                    name=_scope_value(scopes, "name") or f"ONVIF {host}",
                    manufacturer=_scope_value(scopes, "hardware"),
                    model=_scope_value(scopes, "model"),
                    xaddrs=xaddrs,
                )
            )
    finally:
        wsd.stop()
    return devices


def _scope_value(scopes: str, key: str) -> str | None:
    match = re.search(rf"onvif://www\.onvif\.org/{key}/([^\s]+)", scopes)
    return match.group(1).replace("%20", " ") if match else None


@router.get("", response_model=OnvifDiscoveryResponse)
def discover_onvif(
    timeout: int = Query(default=4, ge=1, le=15),
    simulate: bool = Query(default=False, description="Forzar modo simulado"),
    _: CurrentUser = Depends(require_staff),
) -> OnvifDiscoveryResponse:
    """Descubre cámaras ONVIF en la red local.

    - `simulate=true` fuerza dispositivos de demo.
    - Si el descubrimiento real falla, también degrada a simulado.
    """
    if simulate:
        return OnvifDiscoveryResponse(simulated=True, devices=_simulated_devices())

    try:
        devices = _real_discovery(timeout)
        if not devices:
            # Sin resultados reales: ofrecer demo para no bloquear el flujo.
            return OnvifDiscoveryResponse(simulated=True, devices=_simulated_devices())
        return OnvifDiscoveryResponse(simulated=False, devices=devices)
    except Exception:
        return OnvifDiscoveryResponse(simulated=True, devices=_simulated_devices())
