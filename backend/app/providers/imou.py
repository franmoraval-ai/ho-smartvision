"""Proveedor Imou / Lechange Open API (cubre cámaras Imou/Dahua de consumo).

El operador registra una cuenta en la Imou Open Platform
(https://open.imoulife.com) y obtiene `appId`/`appSecret` (IMOU_APP_ID /
IMOU_APP_SECRET). Las cámaras del cliente se vinculan a esa cuenta.

Protocolo de la OpenAPI (POST JSON a `{base}/openapi/{method}`):

    {
      "system": {"ver":"1.0","sign":"<md5>","appId":"<appId>",
                 "time":"<unix>","nonce":"<random>"},
      "id": "<request-id>",
      "params": { ... }
    }

  sign = md5(f"time:{time},nonce:{nonce},appSecret:{appSecret}")
  Respuesta: {"result": {"code":"0","msg":"...","data": {...}}, "id": "..."}
  (code == "0" -> éxito)

NOTA: los nombres exactos de algunos campos pueden variar según la versión de la
API/región; el parseo del stream es defensivo (busca hls/flv/rtmp). Verifícalos
en la consola de la Imou Open Platform con tu cuenta.
"""
from __future__ import annotations

import hashlib
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

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

_TOKEN_INVALID_CODES = {"TK1002", "OP1009", "OP1002"}


class ImouProvider:
    """Cliente del cloud de Imou/Lechange con caché de accessToken en memoria."""

    name = "imou"
    cloud = True

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: str | None = None
        self._token_expiry_epoch: float = 0.0

    # -- Configuración -------------------------------------------------------
    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.imou_app_id and s.imou_app_secret)

    def _base(self) -> str:
        return get_settings().imou_api_base.rstrip("/")

    # -- HTTP / firma --------------------------------------------------------
    def _call(self, method: str, params: dict) -> dict:
        s = get_settings()
        ts = str(int(time.time()))
        nonce = uuid.uuid4().hex
        sign_raw = f"time:{ts},nonce:{nonce},appSecret:{s.imou_app_secret}"
        sign = hashlib.md5(sign_raw.encode()).hexdigest()
        body = {
            "system": {
                "ver": "1.0",
                "sign": sign,
                "appId": s.imou_app_id,
                "time": ts,
                "nonce": nonce,
            },
            "id": nonce,
            "params": params,
        }
        try:
            resp = httpx.post(
                f"{self._base()}/openapi/{method}", json=body, timeout=15.0
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Error de red con Imou: {exc}") from exc
        except ValueError as exc:
            raise ProviderError("Respuesta no-JSON de Imou") from exc

        result = payload.get("result") or {}
        code = str(result.get("code", ""))
        if code != "0":
            msg = result.get("msg") or "Error desconocido de Imou"
            raise ProviderError(f"Imou [{code}]: {msg}", code=code)
        return result.get("data") or {}

    # -- Token ---------------------------------------------------------------
    def _get_token(self, *, force: bool = False) -> str:
        if not self.is_configured():
            raise ProviderNotConfigured(
                "Imou no está configurado (faltan IMOU_APP_ID / IMOU_APP_SECRET)."
            )
        with self._lock:
            now = time.time()
            if not force and self._token and now < self._token_expiry_epoch:
                return self._token
            data = self._call("accessToken", {})
            token = data.get("accessToken")
            if not token:
                raise ProviderError("Imou no devolvió accessToken")
            # expireTime en segundos de validez; margen de 5 min.
            expire_s = float(data.get("expireTime", 0) or 0)
            self._token = token
            self._token_expiry_epoch = now + (expire_s - 300 if expire_s else 3000)
            return token

    # -- Live stream ---------------------------------------------------------
    @staticmethod
    def _pick_url(streams: list[dict], protocol: StreamProtocol) -> tuple[str, StreamProtocol]:
        # Preferencia: el protocolo pedido, luego hls, flv, rtmp.
        order = [protocol, StreamProtocol.hls, StreamProtocol.flv, StreamProtocol.rtmp]
        for proto in order:
            for st in streams:
                url = st.get(proto.value) or st.get(f"{proto.value}Url")
                if url:
                    return url, proto
        raise ProviderError("Imou no devolvió ninguna URL de reproducción")

    def get_live_stream(
        self,
        creds: CameraCredentials,
        *,
        protocol: StreamProtocol | None = None,
    ) -> StreamInfo:
        if not creds.device_serial:
            raise ProviderError("Imou requiere el deviceId del dispositivo")
        protocol = protocol or StreamProtocol.hls
        channel = str(creds.channel or 0)

        params = {
            "token": self._get_token(),
            "deviceId": creds.device_serial,
            "channelId": channel,
        }

        def _live(p: dict) -> dict:
            # Asegura la sesión de live y consulta las URLs disponibles.
            try:
                self._call("bindDeviceLive", {**p, "streamId": 0})
            except ProviderError:
                # Puede estar ya vinculado; continuamos a consultar el stream.
                pass
            return self._call("getLiveStreamInfo", p)

        try:
            data = _live(params)
        except ProviderError as exc:
            if exc.code in _TOKEN_INVALID_CODES:
                params["token"] = self._get_token(force=True)
                data = _live(params)
            else:
                raise

        streams = data.get("streams") or data.get("data") or []
        if isinstance(streams, dict):
            streams = [streams]
        url, proto = self._pick_url(streams, protocol)

        return StreamInfo(
            url=url,
            protocol=proto,
            provider=self.name,
            # La OpenAPI no siempre expone caducidad; asumimos ~1h.
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    # -- Device list ---------------------------------------------------------
    def list_devices(self) -> list[ProviderDevice]:
        data = self._call(
            "deviceBaseList", {"token": self._get_token(), "limit": 50}
        )
        rows = data.get("deviceList") or data.get("list") or []
        devices: list[ProviderDevice] = []
        for row in rows:
            devices.append(
                ProviderDevice(
                    serial=row.get("deviceId") or row.get("sn") or "",
                    name=row.get("name") or row.get("deviceName"),
                    online=(str(row.get("status", "")).lower() in ("1", "online")),
                    channels=int(row.get("channelNum") or row.get("channels") or 1),
                    model=row.get("deviceModel") or row.get("model"),
                )
            )
        return devices
