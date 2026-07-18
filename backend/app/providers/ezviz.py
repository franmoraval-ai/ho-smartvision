"""Proveedor Ezviz Open Platform (cubre cámaras Hikvision/Ezviz).

Usa la "Local API" (lapp) de la Ezviz Open Platform. El operador registra una
cuenta de desarrollador en https://open.ezviz.com y obtiene `appKey`/`appSecret`
(configurados como EZVIZ_APP_KEY / EZVIZ_APP_SECRET). Las cámaras del cliente se
vinculan a esa cuenta por número de serie + código de verificación.

Endpoints usados (POST form-urlencoded, respuesta JSON con `code` == "200"):
  - /api/lapp/token/get          -> accessToken (caché ~7 días)
  - /api/lapp/live/address/get   -> URL de reproducción en vivo (HLS/FLV)

Docs: https://open.ezviz.com/  (referencia de la Open Platform).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings
from app.providers.base import (
    CameraCredentials,
    ProviderDevice,
    ProviderError,
    ProviderNotConfigured,
    StreamInfo,
    StreamProtocol,
)

# Mapeo de protocolo -> valor numérico que espera la Ezviz Open Platform.
#   1 = ezopen, 2 = hls, 3 = rtmp, 4 = flv
_PROTOCOL_CODE = {
    StreamProtocol.hls: 2,
    StreamProtocol.rtmp: 3,
    StreamProtocol.flv: 4,
}

# Códigos de error de la API que conviene tratar de forma específica.
_TOKEN_INVALID_CODES = {"10002", "10001", "10005", "10032"}


class EzvizProvider:
    """Cliente del cloud de Ezviz con caché de accessToken en memoria."""

    name = "ezviz"
    cloud = True

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: str | None = None
        self._token_expiry_epoch: float = 0.0

    # -- Configuración -------------------------------------------------------
    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.ezviz_app_key and s.ezviz_app_secret)

    def _base(self) -> str:
        return get_settings().ezviz_api_base.rstrip("/")

    # -- HTTP helper ---------------------------------------------------------
    def _post(self, path: str, data: dict[str, str]) -> dict:
        url = f"{self._base()}{path}"
        try:
            resp = httpx.post(url, data=data, timeout=15.0)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:  # red/timeout/status
            raise ProviderError(f"Error de red con Ezviz: {exc}") from exc
        except ValueError as exc:  # JSON inválido
            raise ProviderError("Respuesta no-JSON de Ezviz") from exc

        code = str(payload.get("code", ""))
        if code != "200":
            msg = payload.get("msg") or "Error desconocido de Ezviz"
            raise ProviderError(f"Ezviz [{code}]: {msg}", code=code)
        return payload.get("data") or {}

    # -- Token ---------------------------------------------------------------
    def _get_token(self, *, force: bool = False) -> str:
        if not self.is_configured():
            raise ProviderNotConfigured(
                "Ezviz no está configurado (faltan EZVIZ_APP_KEY / EZVIZ_APP_SECRET)."
            )
        with self._lock:
            now = time.time()
            if not force and self._token and now < self._token_expiry_epoch:
                return self._token

            s = get_settings()
            data = self._post(
                "/api/lapp/token/get",
                {"appKey": s.ezviz_app_key, "appSecret": s.ezviz_app_secret},
            )
            token = data.get("accessToken")
            if not token:
                raise ProviderError("Ezviz no devolvió accessToken")
            # expireTime viene en epoch-ms; renovamos con 5 min de margen.
            expire_ms = float(data.get("expireTime", 0) or 0)
            self._token = token
            self._token_expiry_epoch = (
                (expire_ms / 1000.0) - 300 if expire_ms else now + 6 * 86400
            )
            return token

    # -- Live stream ---------------------------------------------------------
    def get_live_stream(
        self,
        creds: CameraCredentials,
        *,
        protocol: StreamProtocol | None = None,
    ) -> StreamInfo:
        if not creds.device_serial:
            raise ProviderError("Ezviz requiere el número de serie del dispositivo")
        protocol = protocol or StreamProtocol.hls
        proto_code = _PROTOCOL_CODE.get(protocol, _PROTOCOL_CODE[StreamProtocol.hls])

        def _request(token: str) -> dict:
            body = {
                "accessToken": token,
                "deviceSerial": creds.device_serial or "",
                "channelNo": str(creds.channel or 1),
                "protocol": str(proto_code),
                "expireTime": "3600",  # segundos de validez de la URL
            }
            if creds.verify_code:
                body["code"] = creds.verify_code
            return self._post("/api/lapp/live/address/get", body)

        token = self._get_token()
        try:
            data = _request(token)
        except ProviderError as exc:
            # Token caducado/invalidado -> reintenta una vez con token nuevo.
            if exc.code in _TOKEN_INVALID_CODES:
                data = _request(self._get_token(force=True))
            else:
                raise

        url = data.get("url")
        if not url:
            raise ProviderError("Ezviz no devolvió URL de reproducción")

        expires_at: datetime | None = None
        expire_ms = data.get("expireTime")
        if expire_ms:
            try:
                expires_at = datetime.fromtimestamp(
                    float(expire_ms) / 1000.0, tz=timezone.utc
                )
            except (TypeError, ValueError, OSError):
                expires_at = None

        return StreamInfo(
            url=url,
            protocol=protocol,
            provider=self.name,
            expires_at=expires_at,
            extra={"stream_id": data.get("id")} if data.get("id") else {},
        )

    # -- Device list ---------------------------------------------------------
    def list_devices(self) -> list[ProviderDevice]:
        token = self._get_token()
        data = self._post(
            "/api/lapp/device/list",
            {"accessToken": token, "pageStart": "0", "pageSize": "50"},
        )
        # Cuando hay lista, la API devuelve el array en la clave `data` superior;
        # `_post` ya extrae `data`, que aquí es una lista de dispositivos.
        rows = data if isinstance(data, list) else data.get("deviceList", [])  # type: ignore[union-attr]
        devices: list[ProviderDevice] = []
        for row in rows or []:
            devices.append(
                ProviderDevice(
                    serial=row.get("deviceSerial", ""),
                    name=row.get("deviceName"),
                    online=row.get("status") == 1,
                    channels=int(row.get("channelNumber") or 1),
                    model=row.get("model"),
                )
            )
        return devices
