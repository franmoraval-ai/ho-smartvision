-- ============================================================================
-- Ho smartvision — Row Level Security (RLS) y políticas de acceso
-- ----------------------------------------------------------------------------
-- Modelo de acceso:
--   • staff (técnicos/admin)  -> acceso total vía is_staff()
--   • app_users (app móvil)   -> solo los datos de SU cliente (client_id)
--       - owner   : lectura + escritura sobre propiedades/cámaras de su cliente
--       - family  : solo lectura
--       - viewer  : solo lectura
--   • El backend FastAPI usa la service_role key y por diseño BYPASSA RLS.
--     Estas políticas protegen el acceso DIRECTO desde la app móvil.
-- ============================================================================

-- Activar RLS en todas las tablas
alter table public.staff      enable row level security;
alter table public.clients    enable row level security;
alter table public.properties enable row level security;
alter table public.gateways   enable row level security;
alter table public.cameras    enable row level security;
alter table public.events     enable row level security;
alter table public.app_users  enable row level security;

-- ----------------------------------------------------------------------------
-- STAFF
-- Un miembro del staff puede ver su propia fila. La gestión de staff se hace
-- desde el backend (service_role). Los admin pueden ver a todo el staff.
-- ----------------------------------------------------------------------------
drop policy if exists staff_select_self on public.staff;
create policy staff_select_self on public.staff
  for select to authenticated
  using (id = auth.uid() or public.is_staff());

-- ----------------------------------------------------------------------------
-- CLIENTS
-- ----------------------------------------------------------------------------
drop policy if exists clients_select on public.clients;
create policy clients_select on public.clients
  for select to authenticated
  using (public.is_staff() or id in (select public.user_client_ids()));

drop policy if exists clients_staff_write on public.clients;
create policy clients_staff_write on public.clients
  for all to authenticated
  using (public.is_staff())
  with check (public.is_staff());

-- ----------------------------------------------------------------------------
-- PROPERTIES
-- ----------------------------------------------------------------------------
drop policy if exists properties_select on public.properties;
create policy properties_select on public.properties
  for select to authenticated
  using (public.is_staff() or client_id in (select public.user_client_ids()));

drop policy if exists properties_owner_write on public.properties;
create policy properties_owner_write on public.properties
  for all to authenticated
  using (public.is_staff() or public.is_client_owner(client_id))
  with check (public.is_staff() or public.is_client_owner(client_id));

-- ----------------------------------------------------------------------------
-- GATEWAYS  (acceso según la propiedad → cliente)
-- ----------------------------------------------------------------------------
drop policy if exists gateways_select on public.gateways;
create policy gateways_select on public.gateways
  for select to authenticated
  using (
    public.is_staff()
    or property_id in (
      select p.id from public.properties p
      where p.client_id in (select public.user_client_ids())
    )
  );

drop policy if exists gateways_staff_write on public.gateways;
create policy gateways_staff_write on public.gateways
  for all to authenticated
  using (public.is_staff())
  with check (public.is_staff());

-- ----------------------------------------------------------------------------
-- CAMERAS
-- NOTA: la app móvil NO debe poder leer onvif_password_encrypted. Restringir
-- por columnas con un GRANT específico (ver más abajo) o exponer una vista.
-- ----------------------------------------------------------------------------
drop policy if exists cameras_select on public.cameras;
create policy cameras_select on public.cameras
  for select to authenticated
  using (
    public.is_staff()
    or property_id in (
      select p.id from public.properties p
      where p.client_id in (select public.user_client_ids())
    )
  );

drop policy if exists cameras_owner_write on public.cameras;
create policy cameras_owner_write on public.cameras
  for all to authenticated
  using (
    public.is_staff()
    or property_id in (
      select p.id from public.properties p
      where public.is_client_owner(p.client_id)
    )
  )
  with check (
    public.is_staff()
    or property_id in (
      select p.id from public.properties p
      where public.is_client_owner(p.client_id)
    )
  );

-- ----------------------------------------------------------------------------
-- EVENTS  (acceso según la cámara → propiedad → cliente)
-- ----------------------------------------------------------------------------
drop policy if exists events_select on public.events;
create policy events_select on public.events
  for select to authenticated
  using (
    public.is_staff()
    or camera_id in (
      select c.id from public.cameras c
      join public.properties p on p.id = c.property_id
      where p.client_id in (select public.user_client_ids())
    )
  );

-- Solo staff/backend insertan eventos (el gateway usa el backend o service_role).
drop policy if exists events_staff_write on public.events;
create policy events_staff_write on public.events
  for all to authenticated
  using (public.is_staff())
  with check (public.is_staff());

-- ----------------------------------------------------------------------------
-- APP_USERS
-- Cada usuario ve su propia fila; un 'owner' ve a todos los usuarios de su cliente.
-- ----------------------------------------------------------------------------
drop policy if exists app_users_select on public.app_users;
create policy app_users_select on public.app_users
  for select to authenticated
  using (
    public.is_staff()
    or id = auth.uid()
    or public.is_client_owner(client_id)
  );

-- Un 'owner' puede invitar/gestionar usuarios de su propio cliente.
drop policy if exists app_users_owner_write on public.app_users;
create policy app_users_owner_write on public.app_users
  for all to authenticated
  using (public.is_staff() or public.is_client_owner(client_id))
  with check (public.is_staff() or public.is_client_owner(client_id));

-- ----------------------------------------------------------------------------
-- Hardening a nivel de columna: ocultar credenciales ONVIF a la app móvil.
-- Revocamos el acceso por columna al rol `authenticated` y exponemos una vista
-- segura `cameras_public` para que la app móvil consuma SOLO datos no sensibles.
-- (El backend usa service_role y conserva acceso completo.)
-- ----------------------------------------------------------------------------
revoke select (onvif_username, onvif_password_encrypted, onvif_ip,
               provider_verify_code_encrypted)
  on public.cameras from authenticated;

create or replace view public.cameras_public
with (security_invoker = true) as
  select id, property_id, gateway_id, name, rtsp_url, is_active, created_at,
         provider, provider_device_serial, provider_channel
  from public.cameras;

comment on view public.cameras_public is
  'Vista para la app móvil: expone cámaras sin credenciales ONVIF. Respeta RLS (security_invoker).';

grant select on public.cameras_public to authenticated;
