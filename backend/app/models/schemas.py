"""Modelos Pydantic (v2) para validación de entrada/salida de la API."""
from datetime import datetime
from enum import Enum
from ipaddress import IPv4Address
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class AppRole(str, Enum):
    owner = "owner"
    family = "family"
    viewer = "viewer"


class StaffRole(str, Enum):
    admin = "admin"
    technician = "technician"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    """Identidad resuelta a partir del JWT verificado."""
    user_id: UUID
    email: str | None = None
    is_staff: bool = False
    staff_role: StaffRole | None = None
    client_ids: list[UUID] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
class ClientBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


class Client(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class PropertyBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=400)


class PropertyCreate(PropertyBase):
    client_id: UUID


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=400)


class Property(PropertyBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Gateways
# ---------------------------------------------------------------------------
class GatewayBase(BaseModel):
    device_id: str = Field(min_length=1, max_length=120)


class GatewayCreate(GatewayBase):
    property_id: UUID


class Gateway(GatewayBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    property_id: UUID
    last_seen: datetime | None = None
    created_at: datetime


class GatewayHeartbeat(BaseModel):
    """Latido enviado por el Gateway Edge para actualizar `last_seen`."""
    device_id: str = Field(min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Cameras
# La contraseña ONVIF entra en claro (se cifra en el backend) y NUNCA se devuelve.
# ---------------------------------------------------------------------------
class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    rtsp_url: str | None = Field(default=None, max_length=500)
    onvif_ip: IPv4Address | None = None
    onvif_username: str | None = Field(default=None, max_length=120)
    is_active: bool = True


class CameraCreate(CameraBase):
    property_id: UUID
    gateway_id: UUID | None = None
    # Entrada en claro: se cifra antes de persistir.
    onvif_password: str | None = Field(default=None, max_length=200)


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    rtsp_url: str | None = Field(default=None, max_length=500)
    onvif_ip: IPv4Address | None = None
    onvif_username: str | None = Field(default=None, max_length=120)
    onvif_password: str | None = Field(default=None, max_length=200)
    gateway_id: UUID | None = None
    is_active: bool | None = None


class Camera(BaseModel):
    """Salida pública de una cámara: sin credenciales sensibles."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    property_id: UUID
    gateway_id: UUID | None = None
    name: str
    rtsp_url: str | None = None
    onvif_ip: str | None = None
    onvif_username: str | None = None
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
class EventCreate(BaseModel):
    camera_id: UUID
    event_type: str = Field(min_length=1, max_length=60)
    thumbnail_url: str | None = None
    video_clip_url: str | None = None
    metadata: dict = Field(default_factory=dict)


class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    camera_id: UUID
    event_type: str
    timestamp: datetime
    thumbnail_url: str | None = None
    video_clip_url: str | None = None
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# App users (móvil)
# ---------------------------------------------------------------------------
class AppUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    client_id: UUID
    role: AppRole = AppRole.viewer


class AppUserInvite(BaseModel):
    """Invitación emitida por un 'owner' desde la app móvil para su cliente."""
    email: EmailStr
    password: str = Field(min_length=6)
    client_id: UUID
    role: AppRole = AppRole.viewer


class AppUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    email: str
    role: AppRole
    created_at: datetime


# ---------------------------------------------------------------------------
# ONVIF discovery
# ---------------------------------------------------------------------------
class OnvifDevice(BaseModel):
    ip: str
    port: int = 80
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    xaddrs: list[str] = Field(default_factory=list)
    rtsp_hint: str | None = None


class OnvifDiscoveryResponse(BaseModel):
    simulated: bool
    devices: list[OnvifDevice]
