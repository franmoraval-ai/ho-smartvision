-- ============================================================================
-- Ho smartvision — Esquema de base de datos (Supabase / Postgres)
-- ----------------------------------------------------------------------------
-- Ejecutar en el SQL Editor de Supabase en este orden:
--   1) schema.sql   (este archivo: tipos, tablas, índices, helpers, triggers)
--   2) policies.sql (RLS + políticas de acceso)
--   3) seed.sql     (datos de ejemplo, opcional)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Extensiones
-- ----------------------------------------------------------------------------
create extension if not exists "pgcrypto";   -- gen_random_uuid()
create extension if not exists "citext";      -- emails case-insensitive

-- ----------------------------------------------------------------------------
-- Tipos enumerados
-- ----------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'app_role') then
    create type public.app_role as enum ('owner', 'family', 'viewer');
  end if;
  if not exists (select 1 from pg_type where typname = 'staff_role') then
    create type public.staff_role as enum ('admin', 'technician');
  end if;
end$$;

-- ============================================================================
-- TABLA: staff  (técnicos / administradores que usan el panel web)
-- Cada fila enlaza 1:1 con un usuario de Supabase Auth (auth.users).
-- No pertenecen a ningún cliente: tienen acceso operativo global.
-- ============================================================================
create table if not exists public.staff (
  id          uuid primary key references auth.users (id) on delete cascade,
  full_name   text        not null,
  email       citext      not null unique,
  role        public.staff_role not null default 'technician',
  is_active   boolean     not null default true,
  created_at  timestamptz not null default now()
);

comment on table public.staff is 'Técnicos y administradores del panel web. Enlaza con auth.users.';

-- ============================================================================
-- TABLA: clients  (clientes finales: hogares o comercios)
-- ============================================================================
create table if not exists public.clients (
  id          uuid primary key default gen_random_uuid(),
  full_name   text        not null,
  email       citext      not null unique,
  phone       text,
  created_at  timestamptz not null default now()
);

comment on table public.clients is 'Cliente final (residencial o comercio) propietario de las propiedades/cámaras.';

-- ============================================================================
-- TABLA: properties  (ubicaciones físicas del cliente)
-- ============================================================================
create table if not exists public.properties (
  id          uuid primary key default gen_random_uuid(),
  client_id   uuid        not null references public.clients (id) on delete cascade,
  name        text        not null,
  address     text,
  created_at  timestamptz not null default now()
);

create index if not exists idx_properties_client_id on public.properties (client_id);

comment on table public.properties is 'Ubicación física (casa, local) perteneciente a un cliente.';

-- ============================================================================
-- TABLA: gateways  (dispositivos Edge — Raspberry Pi — en cada propiedad)
-- ============================================================================
create table if not exists public.gateways (
  id          uuid primary key default gen_random_uuid(),
  property_id uuid        not null references public.properties (id) on delete cascade,
  device_id   text        not null unique,           -- identificador físico del hardware
  last_seen   timestamptz,                            -- heartbeat más reciente
  created_at  timestamptz not null default now()
);

create index if not exists idx_gateways_property_id on public.gateways (property_id);

comment on table public.gateways is 'Gateway Edge (Raspberry Pi) que descubre cámaras y reenvía eventos.';

-- ============================================================================
-- TABLA: cameras
-- onvif_password_encrypted -> ciphertext Fernet generado por el backend.
-- NUNCA se almacena la contraseña en claro.
-- ============================================================================
create table if not exists public.cameras (
  id                         uuid primary key default gen_random_uuid(),
  property_id                uuid    not null references public.properties (id) on delete cascade,
  gateway_id                 uuid    references public.gateways (id) on delete set null,
  name                       text    not null,
  rtsp_url                   text,
  onvif_ip                   inet,
  onvif_username             text,
  onvif_password_encrypted   text,                 -- Fernet token (no plaintext)
  is_active                  boolean not null default true,
  created_at                 timestamptz not null default now()
);

create index if not exists idx_cameras_property_id on public.cameras (property_id);
create index if not exists idx_cameras_gateway_id  on public.cameras (gateway_id);

comment on table public.cameras is 'Cámara CCTV. Credenciales ONVIF cifradas con Fernet en el backend.';
comment on column public.cameras.onvif_password_encrypted is 'Token Fernet. Descifrar solo en el backend con FERNET_KEY.';

-- ============================================================================
-- TABLA: events  (movimiento, persona, etc. — generados por el gateway)
-- ============================================================================
create table if not exists public.events (
  id              uuid primary key default gen_random_uuid(),
  camera_id       uuid        not null references public.cameras (id) on delete cascade,
  event_type      text        not null,            -- 'motion', 'person', 'offline', ...
  timestamp       timestamptz not null default now(),
  thumbnail_url   text,
  video_clip_url  text,
  metadata        jsonb       not null default '{}'::jsonb
);

create index if not exists idx_events_camera_id on public.events (camera_id);
create index if not exists idx_events_timestamp on public.events ("timestamp" desc);
create index if not exists idx_events_metadata  on public.events using gin (metadata);

comment on table public.events is 'Eventos detectados por las cámaras/gateway (movimiento, persona, etc.).';

-- ============================================================================
-- TABLA: app_users  (usuarios de la app móvil — vinculados a un cliente)
-- id = auth.users.id  → permite mapear auth.uid() a un client_id en las RLS.
-- ============================================================================
create table if not exists public.app_users (
  id          uuid primary key references auth.users (id) on delete cascade,
  client_id   uuid        not null references public.clients (id) on delete cascade,
  email       citext      not null,
  role        public.app_role not null default 'viewer',
  created_at  timestamptz not null default now()
);

create index if not exists idx_app_users_client_id on public.app_users (client_id);

comment on table public.app_users is 'Usuario de la app móvil. Pertenece a un cliente con un rol (owner/family/viewer).';

-- ============================================================================
-- HELPERS para RLS  (SECURITY DEFINER para poder leer las tablas sin recursión)
-- ============================================================================

-- ¿El usuario autenticado es staff activo (técnico/admin)?
create or replace function public.is_staff()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.staff s
    where s.id = auth.uid() and s.is_active = true
  );
$$;

-- IDs de cliente a los que pertenece el usuario autenticado (app móvil).
create or replace function public.user_client_ids()
returns setof uuid
language sql
stable
security definer
set search_path = public
as $$
  select au.client_id from public.app_users au
  where au.id = auth.uid();
$$;

-- ¿El usuario es 'owner' del cliente indicado? (permite escritura desde la app)
create or replace function public.is_client_owner(target_client_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.app_users au
    where au.id = auth.uid()
      and au.client_id = target_client_id
      and au.role = 'owner'
  );
$$;

revoke all on function public.is_staff()            from public;
revoke all on function public.user_client_ids()     from public;
revoke all on function public.is_client_owner(uuid) from public;
grant execute on function public.is_staff()            to authenticated;
grant execute on function public.user_client_ids()     to authenticated;
grant execute on function public.is_client_owner(uuid) to authenticated;
