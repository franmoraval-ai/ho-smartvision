"""Gateway Edge de Ho smartvision — bucle principal.

Ejecuta en una Raspberry Pi dentro de la red local del cliente:
  1. Heartbeat periódico al backend (mantiene `last_seen`).
  2. Descubrimiento ONVIF periódico de cámaras.
  3. Generación/recarga de la configuración de go2rtc (streaming WebRTC/HLS).
  4. Reenvío de eventos al backend (autenticado por API key).

Uso:
    python main.py

Detener con Ctrl+C (o vía systemd: `systemctl stop ho-smartvision-gateway`).
"""
from __future__ import annotations

import logging
import signal
import time
from types import FrameType

import go2rtc_manager
import onvif_discovery
from backend_client import BackendClient
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("gateway.main")

# Bandera de parada controlada (señales SIGINT/SIGTERM).
_running = True


def _handle_stop(signum: int, _frame: FrameType | None) -> None:
    global _running
    logger.info("Señal %s recibida; cerrando…", signum)
    _running = False


def _map_ip_to_camera_id(cameras: list[dict]) -> dict[str, str]:
    """Construye {onvif_ip: camera_id} a partir de las cámaras del backend."""
    mapping: dict[str, str] = {}
    for cam in cameras:
        ip = cam.get("onvif_ip")
        if ip:
            mapping[str(ip)] = cam["id"]
    return mapping


def run() -> None:
    settings = get_settings()
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    logger.info("Gateway %s arrancando…", settings.device_id)

    last_discovery = 0.0
    ip_to_camera: dict[str, str] = {}

    with BackendClient(settings.backend_url, settings.api_key) as backend:
        # Primer heartbeat inmediato (verifica conectividad/credenciales).
        if backend.heartbeat(settings.device_id):
            logger.info("Heartbeat inicial OK.")
        else:
            logger.warning("Heartbeat inicial falló; reintentando en el bucle.")

        while _running:
            now = time.monotonic()

            # --- Descubrimiento ONVIF + go2rtc (cada discovery_interval) ---
            if now - last_discovery >= settings.discovery_interval or not last_discovery:
                last_discovery = now
                logger.info("Descubriendo cámaras ONVIF…")
                cameras = onvif_discovery.discover_and_enrich(
                    settings.onvif_username,
                    settings.onvif_password,
                    timeout=settings.discovery_timeout,
                )
                if cameras:
                    go2rtc_manager.write_config(
                        cameras, settings.go2rtc_config_path
                    )
                    go2rtc_manager.reload(settings.go2rtc_api_url)

                # Refresca el mapa IP→camera_id desde el backend.
                backend_cameras = backend.get_cameras(settings.device_id)
                ip_to_camera = _map_ip_to_camera_id(backend_cameras)

                # Emite un evento de estado por cada cámara descubierta y mapeada.
                for cam in cameras:
                    camera_id = ip_to_camera.get(cam.ip)
                    if camera_id:
                        backend.ingest_event(
                            {
                                "camera_id": camera_id,
                                "event_type": "online",
                                "metadata": {
                                    "source": "gateway",
                                    "device_id": settings.device_id,
                                    "rtsp": bool(cam.rtsp_url),
                                },
                            }
                        )

            # --- Heartbeat ---
            backend.heartbeat(settings.device_id)

            # Espera fraccionada para responder rápido a las señales de parada.
            slept = 0.0
            while _running and slept < settings.heartbeat_interval:
                time.sleep(1)
                slept += 1

    logger.info("Gateway detenido.")


if __name__ == "__main__":
    run()
