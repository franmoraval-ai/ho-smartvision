"""Contrato común para los proveedores de streaming en la nube."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable


class StreamProtocol(str, Enum):
    """Protocolos de reproducción soportados por los clouds de fabricante."""

    hls = "hls"
    flv = "flv"
    rtmp = "rtmp"
    rtsp = "rtsp"

    @property
    def browser_playable(self) -> bool:
        """¿Se puede reproducir directamente en un navegador/WebView?

        HLS es nativo (o vía hls.js) y FLV vía mpegts.js/flv.js. RTSP/RTMP
        requieren transcodificación (p. ej. go2rtc) antes de llegar al cliente.
        """
        return self in (StreamProtocol.hls, StreamProtocol.flv)


class ProviderError(Exception):
    """Error genérico devuelto por el cloud de un fabricante."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ProviderNotConfigured(ProviderError):
    """El proveedor no tiene credenciales de operador configuradas."""


@dataclass(slots=True)
class CameraCredentials:
    """Datos de una cámara necesarios para resolver su stream.

    Según el proveedor se usan unos u otros:
      - Cloud (ezviz/imou): `device_serial`, `channel`, `verify_code`.
      - Directo (reolink/tapo): `host`, `username`, `password`, `channel`.
    """

    device_serial: str | None = None
    channel: int = 1
    verify_code: str | None = None
    host: str | None = None
    username: str | None = None
    password: str | None = None


@dataclass(slots=True)
class StreamInfo:
    """URL de reproducción en vivo devuelta por un proveedor."""

    url: str
    protocol: StreamProtocol
    provider: str
    expires_at: datetime | None = None
    extra: dict = field(default_factory=dict)


@dataclass(slots=True)
class ProviderDevice:
    """Cámara vinculada a la cuenta de operador (para onboarding)."""

    serial: str
    name: str | None = None
    online: bool | None = None
    channels: int = 1
    model: str | None = None


@runtime_checkable
class CameraProvider(Protocol):
    """Interfaz que implementa cada proveedor de cloud/streaming de cámaras."""

    name: str
    #: ¿El proveedor obtiene el stream del cloud del fabricante (sin gateway)?
    #: False para proveedores que requieren un host local alcanzable.
    cloud: bool

    def is_configured(self) -> bool:
        """¿Hay credenciales de operador para usar este proveedor?

        Los proveedores directos (reolink/tapo) no necesitan credenciales de
        operador y devuelven siempre True.
        """
        ...

    def get_live_stream(
        self,
        creds: CameraCredentials,
        *,
        protocol: StreamProtocol | None = None,
    ) -> StreamInfo:
        """Devuelve una URL de reproducción en vivo fresca para la cámara.

        Si `protocol` es None, el proveedor elige su protocolo preferido.
        """
        ...

    def list_devices(self) -> list[ProviderDevice]:
        """Lista las cámaras vinculadas a la cuenta de operador.

        Solo aplica a proveedores cloud (ezviz/imou). Los directos lanzan
        `ProviderError`.
        """
        ...
