"""Cliente HTTP del Gateway Edge hacia el backend FastAPI.

Autentica todas las peticiones con la cabecera `X-Gateway-Key`.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("gateway.backend")


class BackendClient:
    """Wrapper fino sobre httpx para hablar con el backend de Ho smartvision."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 10.0) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-Gateway-Key": api_key},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BackendClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def heartbeat(self, device_id: str) -> bool:
        """Actualiza `last_seen` del gateway. Devuelve True si tuvo éxito."""
        try:
            res = self._client.post(
                "/gateways/heartbeat", json={"device_id": device_id}
            )
            res.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Heartbeat rechazado (%s): %s",
                exc.response.status_code,
                exc.response.text,
            )
        except httpx.HTTPError as exc:
            logger.warning("Heartbeat falló: %s", exc)
        return False

    def ingest_event(self, event: dict[str, Any]) -> bool:
        """Envía un evento al backend (`POST /events/ingest`)."""
        try:
            res = self._client.post("/events/ingest", json=event)
            res.raise_for_status()
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Ingesta de evento rechazada (%s): %s",
                exc.response.status_code,
                exc.response.text,
            )
        except httpx.HTTPError as exc:
            logger.warning("Ingesta de evento falló: %s", exc)
        return False

    def get_cameras(self, device_id: str) -> list[dict[str, Any]]:
        """Devuelve las cámaras asignadas a este gateway (para mapear IP->id)."""
        try:
            res = self._client.get(
                "/gateways/cameras", params={"device_id": device_id}
            )
            res.raise_for_status()
            return res.json()
        except httpx.HTTPError as exc:
            logger.warning("No se pudieron obtener las cámaras: %s", exc)
            return []
