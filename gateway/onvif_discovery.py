"""Descubrimiento de cámaras ONVIF en la red local del gateway.

Flujo:
  1. WS-Discovery (multicast) para localizar dispositivos ONVIF.
  2. Por cada dispositivo, usar onvif-zeep para leer info y obtener la URI RTSP
     del perfil principal (requiere credenciales válidas).

Si las librerías ONVIF no están instaladas, las funciones degradan a vacío y
registran un aviso, de modo que el resto del gateway siga funcionando.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger("gateway.onvif")


@dataclass
class DiscoveredCamera:
    """Cámara ONVIF descubierta en la red local."""

    ip: str
    port: int = 80
    xaddrs: list[str] = field(default_factory=list)
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    rtsp_url: str | None = None

    @property
    def stream_key(self) -> str:
        """Identificador estable para usar como nombre de stream en go2rtc."""
        return f"cam_{self.ip.replace('.', '_')}"


def discover(timeout: int = 4) -> list[DiscoveredCamera]:
    """Localiza dispositivos ONVIF vía WS-Discovery. Lista vacía si no hay libs."""
    try:
        from wsdiscovery.discovery import ThreadedWSDiscovery  # type: ignore
    except ImportError:
        logger.warning("WSDiscovery no instalado; se omite el descubrimiento.")
        return []

    wsd = ThreadedWSDiscovery()
    cameras: list[DiscoveredCamera] = []
    try:
        wsd.start()
        services = wsd.searchServices(timeout=timeout)
        seen: set[str] = set()
        for svc in services:
            xaddrs = list(svc.getXAddrs())
            if not xaddrs:
                continue
            parsed = urlparse(xaddrs[0])
            ip = parsed.hostname or ""
            if not ip or ip in seen:
                continue
            seen.add(ip)
            cameras.append(
                DiscoveredCamera(
                    ip=ip,
                    port=parsed.port or 80,
                    xaddrs=xaddrs,
                )
            )
    finally:
        try:
            wsd.stop()
        except Exception:  # pragma: no cover - limpieza best-effort
            pass

    logger.info("WS-Discovery encontró %d dispositivo(s).", len(cameras))
    return cameras


def enrich_with_onvif(
    camera: DiscoveredCamera, username: str, password: str
) -> DiscoveredCamera:
    """Completa info y URI RTSP usando onvif-zeep. Mutación best-effort."""
    try:
        from onvif import ONVIFCamera  # type: ignore
    except ImportError:
        logger.warning("onvif-zeep no instalado; sin enriquecimiento ONVIF.")
        return camera

    try:
        cam = ONVIFCamera(camera.ip, camera.port, username, password)
        info = cam.devicemgmt.GetDeviceInformation()
        camera.manufacturer = getattr(info, "Manufacturer", None)
        camera.model = getattr(info, "Model", None)
        camera.name = camera.name or f"{camera.manufacturer} {camera.model}".strip()

        media = cam.create_media_service()
        profiles = media.GetProfiles()
        if profiles:
            token = profiles[0].token
            uri_req = media.create_type("GetStreamUri")
            uri_req.ProfileToken = token
            uri_req.StreamSetup = {
                "Stream": "RTP-Unicast",
                "Transport": {"Protocol": "RTSP"},
            }
            stream = media.GetStreamUri(uri_req)
            camera.rtsp_url = _inject_credentials(
                stream.Uri, username, password
            )
    except Exception as exc:  # red/credenciales/firmware variados
        logger.warning("ONVIF no respondió en %s: %s", camera.ip, exc)

    return camera


def _inject_credentials(rtsp_url: str, username: str, password: str) -> str:
    """Inserta user:pass en la URL RTSP si no los trae (para go2rtc)."""
    if not username or "@" in rtsp_url:
        return rtsp_url
    parsed = urlparse(rtsp_url)
    netloc = f"{username}:{password}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def discover_and_enrich(
    username: str, password: str, timeout: int = 4
) -> list[DiscoveredCamera]:
    """Descubre y enriquece todas las cámaras en una sola llamada."""
    cameras = discover(timeout=timeout)
    return [enrich_with_onvif(cam, username, password) for cam in cameras]
