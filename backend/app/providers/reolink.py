"""Proveedor Reolink (acceso directo por su API HTTP-FLV).

Reolink no ofrece un cloud abierto con appKey; se accede al propio equipo por
HTTP. Devolvemos una URL HTTP-FLV (reproducible con mpegts.js/flv.js) construida
con el host + usuario + contraseña de la cámara (se reutilizan los campos
`onvif_ip` / `onvif_username` / `onvif_password`).

Requisitos: el `host` debe ser alcanzable desde el cliente (IP local en la misma
red, o DDNS/port-forward). Si la cámara está tras NAT sin exponer, este
proveedor no basta y hace falta el gateway/transcodificación.

Formato FLV de Reolink:
  http://{host}/flv?port=1935&app=bcs&stream=channel{n}_main.bcs&user={u}&password={p}
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


class ReolinkProvider:
    """Construye la URL HTTP-FLV directa de una cámara Reolink."""

    name = "reolink"
    cloud = False

    def is_configured(self) -> bool:  # no requiere credenciales de operador
        return True

    def list_devices(self) -> list[ProviderDevice]:
        raise ProviderError("Reolink no soporta listado de dispositivos por cuenta")

    def get_live_stream(
        self,
        creds: CameraCredentials,
        *,
        protocol: StreamProtocol | None = None,
    ) -> StreamInfo:
        if not creds.host:
            raise ProviderError("Reolink requiere el host/IP de la cámara (onvif_ip)")
        if not creds.username or creds.password is None:
            raise ProviderError("Reolink requiere usuario y contraseña de la cámara")

        host = creds.host
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        host = host.rstrip("/")

        channel = max((creds.channel or 1) - 1, 0)  # Reolink indexa desde 0
        quality = "main"
        user = quote(creds.username, safe="")
        pwd = quote(creds.password, safe="")

        if protocol in (StreamProtocol.rtsp, StreamProtocol.rtmp):
            # RTSP alternativo (requiere transcodificación para el navegador).
            bare = creds.host.split("://", 1)[-1]
            url = (
                f"rtsp://{user}:{pwd}@{bare}:554/"
                f"h264Preview_{(creds.channel or 1):02d}_{quality}"
            )
            return StreamInfo(url=url, protocol=StreamProtocol.rtsp, provider=self.name)

        url = (
            f"{host}/flv?port=1935&app=bcs"
            f"&stream=channel{channel}_{quality}.bcs&user={user}&password={pwd}"
        )
        return StreamInfo(url=url, protocol=StreamProtocol.flv, provider=self.name)
