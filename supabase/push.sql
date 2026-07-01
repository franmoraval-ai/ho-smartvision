-- ============================================================================
-- Ho smartvision — Web Push (sin Firebase)
-- ----------------------------------------------------------------------------
-- Ejecutar en el SQL Editor de Supabase DESPUÉS de schema.sql y policies.sql.
--
-- Qué hace:
--   1) Tabla `push_subscriptions` (una fila por dispositivo/navegador suscrito).
--   2) RLS: cada usuario gestiona sus propias suscripciones; el staff las lee.
--   3) Trigger: al insertar un evento, llama a la Edge Function `notify-event`
--      (vía pg_net) para enviar la notificación push a los suscriptores.
--
-- Requisitos:
--   • Extensión pg_net (se activa abajo; disponible en Supabase).
--   • Config: define la URL de la función y un secreto compartido (ver más abajo).
-- ============================================================================

create extension if not exists pg_net;

-- ----------------------------------------------------------------------------
-- TABLA: push_subscriptions
--   endpoint  -> URL única del push service del navegador
--   p256dh/auth -> claves de la suscripción Web Push (PushSubscription.keys)
-- ----------------------------------------------------------------------------
create table if not exists public.push_subscriptions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users (id) on delete cascade,
  endpoint    text        not null unique,
  p256dh      text        not null,
  auth        text        not null,
  user_agent  text,
  created_at  timestamptz not null default now()
);

create index if not exists idx_push_subs_user_id on public.push_subscriptions (user_id);

comment on table public.push_subscriptions is
  'Suscripciones Web Push (VAPID). Una fila por navegador/dispositivo.';

alter table public.push_subscriptions enable row level security;

-- Cada usuario gestiona (lee/crea/borra) SOLO sus propias suscripciones.
drop policy if exists push_subs_own on public.push_subscriptions;
create policy push_subs_own on public.push_subscriptions
  for all to authenticated
  using (user_id = auth.uid() or public.is_staff())
  with check (user_id = auth.uid());

-- ----------------------------------------------------------------------------
-- TABLA: device_tokens  (tokens FCM de la app móvil — Firebase Cloud Messaging)
--   Se usa para el push NATIVO en Android/iOS. El navegador usa push_subscriptions.
-- ----------------------------------------------------------------------------
create table if not exists public.device_tokens (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users (id) on delete cascade,
  fcm_token   text        not null unique,
  platform    text        not null default 'android',  -- 'android' | 'ios'
  created_at  timestamptz not null default now()
);

create index if not exists idx_device_tokens_user_id on public.device_tokens (user_id);

comment on table public.device_tokens is
  'Tokens FCM de la app móvil (push nativo Android/iOS). Uno por dispositivo.';

alter table public.device_tokens enable row level security;

-- Cada usuario gestiona SOLO sus propios tokens.
drop policy if exists device_tokens_own on public.device_tokens;
create policy device_tokens_own on public.device_tokens
  for all to authenticated
  using (user_id = auth.uid() or public.is_staff())
  with check (user_id = auth.uid());

-- ----------------------------------------------------------------------------
-- CONFIGURACIÓN del trigger (URL de la función + secreto compartido).
-- Sustituye <PROJECT_REF> por el ref de tu proyecto y define un secreto fuerte.
-- Estos valores se guardan como settings de la base de datos.
--
--   alter database postgres set app.settings.edge_url =
--     'https://<PROJECT_REF>.functions.supabase.co/notify-event';
--   alter database postgres set app.settings.webhook_secret = 'UN_SECRETO_LARGO';
--
-- (Alternativa sin SQL: crea un "Database Webhook" desde el dashboard de
--  Supabase apuntando a la Edge Function `notify-event` en INSERT de `events`.)
-- ----------------------------------------------------------------------------

create or replace function public.notify_event_push()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  edge_url text := current_setting('app.settings.edge_url', true);
  secret   text := current_setting('app.settings.webhook_secret', true);
begin
  -- Si no está configurada la URL, no hacemos nada (evita errores en inserts).
  if edge_url is null or edge_url = '' then
    return new;
  end if;

  perform net.http_post(
    url     := edge_url,
    body    := jsonb_build_object('event', to_jsonb(new)),
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'x-webhook-secret', coalesce(secret, '')
    ),
    timeout_milliseconds := 5000
  );

  return new;
end;
$$;

drop trigger if exists on_event_created_notify on public.events;
create trigger on_event_created_notify
  after insert on public.events
  for each row execute function public.notify_event_push();
