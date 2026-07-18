"""Configuración de pytest para el backend.

Fija variables de entorno mínimas para que `Settings` (Pydantic) no falle al
instanciarse durante los tests, y limpia la caché del singleton.
"""
import os

import pytest

_DEFAULT_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role",
    "SUPABASE_ANON_KEY": "test-anon",
    # Clave Fernet válida (32 bytes url-safe base64) solo para tests.
    "FERNET_KEY": "zBQhX8m1cS9y2Yk7t0v3pR6nJ4dK5wL8aQ2eS7uH0cM=",
    "EZVIZ_APP_KEY": "test-appkey",
    "EZVIZ_APP_SECRET": "test-appsecret",
    "EZVIZ_API_BASE": "https://open.example.com",
    "IMOU_APP_ID": "test-appid",
    "IMOU_APP_SECRET": "test-appsecret",
    "IMOU_API_BASE": "https://openapi.example.com",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for key, value in _DEFAULT_ENV.items():
        monkeypatch.setenv(key, value)
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
