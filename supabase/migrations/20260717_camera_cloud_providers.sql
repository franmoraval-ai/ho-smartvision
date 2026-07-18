-- ============================================================================
-- Migración: proveedores de streaming en la nube por cámara
-- ----------------------------------------------------------------------------
-- Permite que cada cámara obtenga su vídeo del cloud del fabricante
-- (Ezviz/Hikvision, Imou/Dahua) o por acceso directo (Reolink, Tapo), sin
-- depender de un gateway físico (Raspberry + go2rtc).
--
-- Ejecutar en el SQL Editor de Supabase. Es idempotente.
-- ============================================================================

alter table public.cameras
  add column if not exists provider                       text not null default 'local',
  add column if not exists provider_device_serial         text,
  add column if not exists provider_channel               int  not null default 1,
  add column if not exists provider_verify_code_encrypted text;   -- Fernet token

-- Restringe los valores válidos de provider.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'cameras_provider_check'
  ) then
    alter table public.cameras
      add constraint cameras_provider_check
      check (provider in ('local', 'ezviz', 'imou', 'reolink', 'tapo'));
  end if;
end$$;

comment on column public.cameras.provider is
  'Origen del stream: local (gateway/go2rtc), ezviz, imou, reolink, tapo.';
comment on column public.cameras.provider_device_serial is
  'Número de serie/UID en el cloud del fabricante (Ezviz/Imou).';
comment on column public.cameras.provider_verify_code_encrypted is
  'Token Fernet del código de verificación/cifrado del dispositivo (Ezviz).';

-- Oculta el código de verificación cifrado a la app móvil (rol authenticated).
revoke select (provider_verify_code_encrypted)
  on public.cameras from authenticated;

-- Reexpone la vista pública incluyendo los campos de proveedor no sensibles.
create or replace view public.cameras_public
with (security_invoker = true) as
  select id, property_id, gateway_id, name, rtsp_url, is_active, created_at,
         provider, provider_device_serial, provider_channel
  from public.cameras;

grant select on public.cameras_public to authenticated;
