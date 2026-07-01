-- ============================================================================
-- Ho smartvision — Datos de ejemplo (opcional, solo para desarrollo)
-- ----------------------------------------------------------------------------
-- Ejecutar DESPUÉS de schema.sql y policies.sql.
-- Nota: app_users.id y staff.id deben coincidir con IDs reales de auth.users.
--       Para pruebas, crea primero los usuarios en Authentication > Users y
--       reemplaza los UUID de ejemplo de abajo.
-- ============================================================================

-- Cliente de ejemplo
insert into public.clients (id, full_name, email, phone)
values
  ('11111111-1111-1111-1111-111111111111', 'Familia García', 'familia.garcia@example.com', '+34600000000')
on conflict (id) do nothing;

-- Propiedad
insert into public.properties (id, client_id, name, address)
values
  ('22222222-2222-2222-2222-222222222222',
   '11111111-1111-1111-1111-111111111111',
   'Casa principal', 'Calle Mayor 1, Madrid')
on conflict (id) do nothing;

-- Gateway (Raspberry Pi)
insert into public.gateways (id, property_id, device_id, last_seen)
values
  ('33333333-3333-3333-3333-333333333333',
   '22222222-2222-2222-2222-222222222222',
   'rpi-garcia-001', now())
on conflict (id) do nothing;

-- Cámara (sin credenciales ONVIF reales — se cifran desde el backend)
insert into public.cameras (id, property_id, gateway_id, name, rtsp_url, onvif_ip, onvif_username, is_active)
values
  ('44444444-4444-4444-4444-444444444444',
   '22222222-2222-2222-2222-222222222222',
   '33333333-3333-3333-3333-333333333333',
   'Entrada principal',
   'rtsp://192.168.1.50:554/stream1',
   '192.168.1.50', 'admin', true)
on conflict (id) do nothing;

-- Evento de ejemplo
insert into public.events (camera_id, event_type, thumbnail_url, metadata)
values
  ('44444444-4444-4444-4444-444444444444',
   'motion',
   'https://example.com/thumbnails/sample.jpg',
   '{"confidence": 0.92, "zone": "puerta"}'::jsonb)
on conflict do nothing;

-- ============================================================================
-- STAFF (panel web) — el id debe ser el UID real de Authentication > Users.
-- Ejemplo del primer administrador del proyecto:
-- ----------------------------------------------------------------------------
insert into public.staff (id, full_name, email, role)
values
  ('4d6525a9-f910-4ea1-aeb0-398a24019f8d', 'Francisco', 'franmoraval@gmail.com', 'admin')
on conflict (id) do nothing;
