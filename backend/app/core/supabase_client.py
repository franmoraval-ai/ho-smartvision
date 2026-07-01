"""Clientes de Supabase reutilizables.

- `get_service_client()`  -> usa la service_role key (BYPASSA RLS). Solo backend.
- `get_anon_client()`     -> usa la anon key (login y operaciones públicas).
"""
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_service_client() -> Client:
    """Cliente con privilegios de service_role. NO exponer al exterior.

    Bypassa Row Level Security: úsalo solo tras validar permisos en el backend.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@lru_cache
def get_anon_client() -> Client:
    """Cliente con la anon key (respeta RLS). Útil para login con contraseña."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
