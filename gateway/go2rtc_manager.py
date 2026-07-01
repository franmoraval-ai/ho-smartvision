"""Generación de configuración para go2rtc y recarga en caliente.

go2rtc (https://github.com/AlexxIT/go2rtc) reexpone las cámaras RTSP como
WebRTC/HLS de baja latencia, ideal para la app móvil y el panel web.

Este módulo:
  - Escribe/actualiza el `go2rtc.yaml` con un stream por cámara descubierta.
  - Pide a go2rtc que recargue la configuración vía su API REST.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

import httpx
import yaml

from onvif_discovery import DiscoveredCamera

logger = logging.getLogger("gateway.go2rtc")


def build_config(
    cameras: Iterable[DiscoveredCamera],
    ip_to_camera: dict[str, str] | None = None,
) -> dict:
    """Construye el dict de configuración de go2rtc a partir de las cámaras.

    El nombre de cada stream es el `camera_id` (UUID del backend) cuando la
    cámara está mapeada por IP, de modo que coincida con lo que piden la app
    móvil y el panel web (`stream.html?src=<camera_id>`). Si no hay mapeo, se
    usa el `stream_key` basado en IP como respaldo.
    """
    ip_to_camera = ip_to_camera or {}
    streams: dict[str, str] = {}
    for cam in cameras:
        if cam.rtsp_url:
            key = ip_to_camera.get(cam.ip) or cam.stream_key
            streams[key] = cam.rtsp_url

    return {
        # API local (panel de go2rtc + endpoints REST/WebRTC).
        "api": {"listen": ":1984"},
        # RTSP de salida re-empaquetado.
        "rtsp": {"listen": ":8554"},
        # WebRTC para la app móvil / web (baja latencia).
        "webrtc": {"listen": ":8555"},
        "streams": streams,
    }


def write_config(
    cameras: Iterable[DiscoveredCamera],
    path: str,
    ip_to_camera: dict[str, str] | None = None,
) -> int:
    """Escribe el go2rtc.yaml. Devuelve el número de streams configurados."""
    config = build_config(cameras, ip_to_camera)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(config, fh, sort_keys=False, allow_unicode=True)
    n = len(config["streams"])
    logger.info("go2rtc.yaml escrito en %s con %d stream(s).", path, n)
    return n


def reload(api_url: str) -> bool:
    """Solicita a go2rtc que recargue su configuración. True si lo logra."""
    try:
        res = httpx.post(f"{api_url}/api/restart", timeout=5.0)
        res.raise_for_status()
        logger.info("go2rtc recargado correctamente.")
        return True
    except httpx.HTTPError as exc:
        logger.warning("No se pudo recargar go2rtc: %s", exc)
        return False
