"""Proveedores de streaming en la nube de fabricantes de cámaras.

En lugar de un gateway físico (Raspberry + go2rtc + túnel), cada cámara puede
apoyarse en el *cloud* que su fabricante ya ofrece (Ezviz/Hikvision, Imou/Dahua,
Reolink...). El backend pide bajo demanda una URL de reproducción en vivo
(HLS/FLV) que web y app reproducen directamente.

La capa es agnóstica al fabricante: cada proveedor implementa `CameraProvider`
y se registra en `registry.get_provider`.
"""
from app.providers.base import (
    CameraCredentials,
    CameraProvider,
    ProviderDevice,
    ProviderError,
    ProviderNotConfigured,
    StreamInfo,
    StreamProtocol,
)
from app.providers.registry import available_providers, get_provider

__all__ = [
    "CameraCredentials",
    "CameraProvider",
    "ProviderDevice",
    "ProviderError",
    "ProviderNotConfigured",
    "StreamInfo",
    "StreamProtocol",
    "available_providers",
    "get_provider",
]
