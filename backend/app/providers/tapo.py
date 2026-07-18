"""Proveedor Tapo / TP-Link (acceso directo por RTSP local).

Tapo no publica un cloud abierto con appKey; la vía soportada es el RTSP local
de la cámara. Se construye la URL con el host + usuario + contraseña de la
"Cuenta de cámara" configurada en la app Tapo (se reutilizan los campos
`onvif_ip` / `onvif_username` / `onvif_password`).

RTSP no es reproducible directamente en un navegador: requiere
transcodificación (p. ej. go2rtc en el gateway) para llegar a web/app como
HLS/WebRTC. Este proveedor deja lista la URL correcta.

Formato RTSP de Tapo:
  rtsp://{user}:{pass}@{host}:554/stream1   (alta calidad)
  rtsp://{user}:{pass}@{host}:554/stream2   (baja calidad)
"""
from __future__ import annotations

from urllib.parse import quote

from app.providers.base import (
    CameraCredentials,
    ProviderDevice,
    ProviderError,
    StreamInfo,
    StreamProtocol,
)


class TapoProvider:
    """Construye la URL RTSP directa de una cámara Tapo/TP-Link."""

    name = "tapo"
    cloud = False

    def is_configured(self) -> bool:  # no requiere credenciales de operador
        return True

    def list_devices(self) -> list[ProviderDevice]:
        raise ProviderError("Tapo no soporta listado de dispositivos por cuenta")

    def get_live_stream(
        self,
        creds: CameraCredentials,
        *,
        protocol: StreamProtocol | None = None,
    ) -> StreamInfo:
        if not creds.host:
            raise ProviderError("Tapo requiere el host/IP de la cámara (onvif_ip)")
        if not creds.username or creds.password is None:
            raise ProviderError("Tapo requiere usuario y contraseña de la cámara")

        bare = creds.host.split("://", 1)[-1].rstrip("/")
        user = quote(creds.username, safe="")
        pwd = quote(creds.password, safe="")
        # channel 1 -> stream1 (alta), channel 2 -> stream2 (baja).
        stream = "stream2" if (creds.channel or 1) >= 2 else "stream1"
        url = f"rtsp://{user}:{pwd}@{bare}:554/{stream}"
        return StreamInfo(url=url, protocol=StreamProtocol.rtsp, provider=self.name)
