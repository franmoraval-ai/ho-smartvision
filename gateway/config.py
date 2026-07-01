"""Configuración del Gateway Edge (cargada desde variables de entorno / .env).

Pensado para ejecutarse en una Raspberry Pi dentro de la red local del cliente.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    """Ajustes del gateway."""

    # Identificador físico único de este gateway (debe existir como `device_id`
    # en la tabla `gateways`, registrado desde el panel de técnicos).
    device_id: str = field(default_factory=lambda: _require("GATEWAY_DEVICE_ID"))

    # URL base del backend FastAPI (p. ej. https://ho-smartvision-api.onrender.com).
    backend_url: str = field(
        default_factory=lambda: _require("BACKEND_URL").rstrip("/")
    )

    # API key compartida con el backend (GATEWAY_API_KEY del backend).
    api_key: str = field(default_factory=lambda: _require("GATEWAY_API_KEY"))

    # Credenciales ONVIF por defecto para probar las cámaras descubiertas.
    onvif_username: str = field(
        default_factory=lambda: os.getenv("ONVIF_USERNAME", "admin")
    )
    onvif_password: str = field(
        default_factory=lambda: os.getenv("ONVIF_PASSWORD", "")
    )

    # Intervalo de heartbeat (segundos).
    heartbeat_interval: int = field(
        default_factory=lambda: int(os.getenv("HEARTBEAT_INTERVAL", "30"))
    )

    # Intervalo de re-descubrimiento ONVIF (segundos).
    discovery_interval: int = field(
        default_factory=lambda: int(os.getenv("DISCOVERY_INTERVAL", "300"))
    )

    # Timeout de WS-Discovery (segundos).
    discovery_timeout: int = field(
        default_factory=lambda: int(os.getenv("DISCOVERY_TIMEOUT", "4"))
    )

    # Ruta donde escribir la configuración generada para go2rtc.
    go2rtc_config_path: str = field(
        default_factory=lambda: os.getenv(
            "GO2RTC_CONFIG_PATH", "/etc/go2rtc/go2rtc.yaml"
        )
    )

    # URL de la API de go2rtc (para recargar configuración sin reiniciar).
    go2rtc_api_url: str = field(
        default_factory=lambda: os.getenv(
            "GO2RTC_API_URL", "http://127.0.0.1:1984"
        ).rstrip("/")
    )


def get_settings() -> Settings:
    """Construye los ajustes validando las variables obligatorias."""
    return Settings()
