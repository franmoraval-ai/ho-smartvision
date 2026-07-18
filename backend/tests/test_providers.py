"""Tests unitarios de los proveedores de streaming de cámaras."""
import httpx
import pytest

from app.providers.base import (
    CameraCredentials,
    ProviderError,
    StreamProtocol,
)
from app.providers.ezviz import EzvizProvider
from app.providers.imou import ImouProvider
from app.providers.reolink import ReolinkProvider
from app.providers.tapo import TapoProvider


# ---------------------------------------------------------------------------
# StreamProtocol
# ---------------------------------------------------------------------------
def test_browser_playable_flags():
    assert StreamProtocol.hls.browser_playable is True
    assert StreamProtocol.flv.browser_playable is True
    assert StreamProtocol.rtsp.browser_playable is False
    assert StreamProtocol.rtmp.browser_playable is False


# ---------------------------------------------------------------------------
# Reolink (construcción de URL, sin red)
# ---------------------------------------------------------------------------
def test_reolink_flv_url():
    p = ReolinkProvider()
    info = p.get_live_stream(
        CameraCredentials(host="192.168.1.9", username="admin", password="p@ss", channel=1)
    )
    assert info.protocol is StreamProtocol.flv
    assert info.url.startswith("http://192.168.1.9/flv?")
    assert "channel0_main.bcs" in info.url
    assert "user=admin" in info.url
    assert "password=p%40ss" in info.url  # contraseña url-encoded


def test_reolink_rtsp_variant_channel2():
    p = ReolinkProvider()
    info = p.get_live_stream(
        CameraCredentials(host="cam.ddns.net", username="u", password="pw", channel=2),
        protocol=StreamProtocol.rtsp,
    )
    assert info.protocol is StreamProtocol.rtsp
    assert info.url == "rtsp://u:pw@cam.ddns.net:554/h264Preview_02_main"


def test_reolink_requires_host():
    with pytest.raises(ProviderError):
        ReolinkProvider().get_live_stream(CameraCredentials(username="u", password="p"))


# ---------------------------------------------------------------------------
# Tapo (construcción de URL RTSP, sin red)
# ---------------------------------------------------------------------------
def test_tapo_rtsp_url_high_and_low():
    p = TapoProvider()
    hi = p.get_live_stream(
        CameraCredentials(host="10.0.0.5", username="cam", password="s3cret", channel=1)
    )
    assert hi.protocol is StreamProtocol.rtsp
    assert hi.url == "rtsp://cam:s3cret@10.0.0.5:554/stream1"

    lo = p.get_live_stream(
        CameraCredentials(host="10.0.0.5", username="cam", password="s3cret", channel=2)
    )
    assert lo.url.endswith("/stream2")


def test_tapo_password_encoded():
    info = TapoProvider().get_live_stream(
        CameraCredentials(host="10.0.0.5", username="cam", password="a/b:c")
    )
    assert "a%2Fb%3Ac" in info.url


# ---------------------------------------------------------------------------
# Ezviz (HTTP mockeado)
# ---------------------------------------------------------------------------
def _fake_post_factory(routes: dict[str, dict]):
    """Devuelve un stub de httpx.post que responde según el path de la URL."""

    def _post(url, data=None, json=None, timeout=None):
        for path, payload in routes.items():
            if path in url:
                return httpx.Response(200, json=payload, request=httpx.Request("POST", url))
        raise AssertionError(f"URL no esperada en el test: {url}")

    return _post


def test_ezviz_get_live_stream(monkeypatch):
    routes = {
        "/api/lapp/token/get": {
            "code": "200",
            "data": {"accessToken": "tok123", "expireTime": 9999999999000},
        },
        "/api/lapp/live/address/get": {
            "code": "200",
            "data": {
                "url": "https://cdn.example.com/live.m3u8",
                "expireTime": 9999999999000,
                "id": "stream-1",
            },
        },
    }
    monkeypatch.setattr("app.providers.ezviz.httpx.post", _fake_post_factory(routes))

    info = EzvizProvider().get_live_stream(
        CameraCredentials(device_serial="BA1234567", channel=1)
    )
    assert info.provider == "ezviz"
    assert info.protocol is StreamProtocol.hls
    assert info.url == "https://cdn.example.com/live.m3u8"
    assert info.extra["stream_id"] == "stream-1"


def test_ezviz_api_error_raises(monkeypatch):
    routes = {
        "/api/lapp/token/get": {
            "code": "200",
            "data": {"accessToken": "tok", "expireTime": 9999999999000},
        },
        "/api/lapp/live/address/get": {"code": "20007", "msg": "device offline"},
    }
    monkeypatch.setattr("app.providers.ezviz.httpx.post", _fake_post_factory(routes))
    with pytest.raises(ProviderError) as exc:
        EzvizProvider().get_live_stream(CameraCredentials(device_serial="X"))
    assert exc.value.code == "20007"


def test_ezviz_requires_serial(monkeypatch):
    monkeypatch.setattr(
        "app.providers.ezviz.httpx.post", _fake_post_factory({})
    )
    with pytest.raises(ProviderError):
        EzvizProvider().get_live_stream(CameraCredentials())


def test_ezviz_list_devices(monkeypatch):
    routes = {
        "/api/lapp/token/get": {
            "code": "200",
            "data": {"accessToken": "tok", "expireTime": 9999999999000},
        },
        "/api/lapp/device/list": {
            "code": "200",
            "data": [
                {
                    "deviceSerial": "AA1",
                    "deviceName": "Entrada",
                    "status": 1,
                    "model": "C6N",
                    "channelNumber": 1,
                }
            ],
        },
    }
    monkeypatch.setattr("app.providers.ezviz.httpx.post", _fake_post_factory(routes))
    devices = EzvizProvider().list_devices()
    assert len(devices) == 1
    assert devices[0].serial == "AA1"
    assert devices[0].online is True


# ---------------------------------------------------------------------------
# Imou (HTTP mockeado)
# ---------------------------------------------------------------------------
def test_imou_get_live_stream(monkeypatch):
    routes = {
        "/openapi/accessToken": {
            "result": {"code": "0", "data": {"accessToken": "tok", "expireTime": 3600}}
        },
        "/openapi/bindDeviceLive": {"result": {"code": "0", "data": {}}},
        "/openapi/getLiveStreamInfo": {
            "result": {
                "code": "0",
                "data": {"streams": [{"hls": "https://imou.example.com/live.m3u8"}]},
            }
        },
    }
    monkeypatch.setattr("app.providers.imou.httpx.post", _fake_post_factory(routes))
    info = ImouProvider().get_live_stream(
        CameraCredentials(device_serial="DEV1", channel=0)
    )
    assert info.provider == "imou"
    assert info.protocol is StreamProtocol.hls
    assert info.url == "https://imou.example.com/live.m3u8"
