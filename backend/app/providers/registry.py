"""Registro de proveedores de streaming en la nube.

Nuevos fabricantes (Imou/Dahua, Reolink...) se añaden implementando
`CameraProvider` y registrándolos aquí, sin tocar el resto del backend.
"""
from __future__ import annotations

from app.providers.base import CameraProvider, ProviderError
from app.providers.ezviz import EzvizProvider
from app.providers.imou import ImouProvider
from app.providers.reolink import ReolinkProvider
from app.providers.tapo import TapoProvider

# Instancias singleton (mantienen la caché de token entre peticiones).
_PROVIDERS: dict[str, CameraProvider] = {
    EzvizProvider.name: EzvizProvider(),
    ImouProvider.name: ImouProvider(),
    ReolinkProvider.name: ReolinkProvider(),
    TapoProvider.name: TapoProvider(),
}


def get_provider(name: str) -> CameraProvider:
    """Devuelve el proveedor por nombre. Lanza ProviderError si no existe."""
    provider = _PROVIDERS.get((name or "").lower())
    if provider is None:
        raise ProviderError(f"Proveedor de cámara no soportado: {name!r}")
    return provider


def available_providers() -> list[str]:
    """Nombres de proveedores con credenciales de operador configuradas."""
    return [name for name, p in _PROVIDERS.items() if p.is_configured()]


def all_providers() -> list[CameraProvider]:
    """Todas las instancias de proveedor registradas."""
    return list(_PROVIDERS.values())
