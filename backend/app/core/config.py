"""Configuración central de la aplicación (cargada desde variables de entorno)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes tipados de la aplicación.

    Se cargan desde el archivo `.env` o desde el entorno del proceso.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Supabase ---
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str
    # Secreto JWT legacy (HS256). Opcional: los proyectos nuevos usan
    # "JWT Signing Keys" asimétricas y se validan vía JWKS.
    supabase_jwt_secret: str = ""

    # --- Cifrado de credenciales ONVIF (Fernet) ---
    fernet_key: str

    # --- Seguridad del Gateway Edge ---
    gateway_api_key: str = ""

    # --- CORS (orígenes separados por coma) ---
    cors_origins: str = "http://localhost:3000"

    # --- App ---
    environment: str = "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Devuelve los orígenes CORS como lista limpia."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una instancia cacheada de Settings (singleton)."""
    return Settings()  # type: ignore[call-arg]
