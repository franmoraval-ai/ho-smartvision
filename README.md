# Ho smartvision

Plataforma de gestión de cámaras CCTV para clientes residenciales y pequeños comercios.
Servicio de "rescate": los técnicos configuran cámaras existentes vía **ONVIF**.

## Arquitectura

```
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  App Móvil        │        │  Panel Web       │        │  Edge Gateway     │
│  (Flutter)        │        │  (Next.js 15)    │        │  (Raspberry Pi)   │
│  Clientes         │        │  Técnicos        │        │  ONVIF + go2rtc   │
└────────┬─────────┘        └────────┬─────────┘        └────────┬─────────┘
         │ JWT (RLS)                 │ JWT (service)             │ API key
         ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Backend FastAPI (Python)                          │
│   Auth Supabase · CRUD · /discover-onvif · webhooks de eventos             │
└────────────────────────────────────────┬──────────────────────────────────┘
                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            Supabase (Postgres + Auth + Storage + Realtime)                 │
│                       RLS activado en todas las tablas                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Principio de seguridad
- **App móvil (Flutter)** → habla **directo** con Supabase usando el JWT del usuario. Las **políticas RLS** garantizan que cada cliente solo ve sus datos.
- **Panel web (técnicos)** → habla con **FastAPI**, que usa la `service_role key` (bypassa RLS) pero valida que el JWT pertenezca a un miembro del `staff`.
- **Contraseñas ONVIF** → nunca se guardan en claro. Se cifran con **Fernet** en el backend antes de persistirlas.

## Estructura del repositorio

```
.
├── supabase/          # schema.sql, policies.sql, seed.sql (Postgres + RLS)
├── backend/           # API FastAPI (supabase-py, JWT, ONVIF, eventos)
├── web/               # Panel de técnicos (Next.js 15 + Tailwind + shadcn/ui)
├── edge-gateway/      # Script para Raspberry Pi (ONVIF discovery + go2rtc)  [próximamente]
└── mobile/            # App Flutter del cliente                              [próximamente]
```

## Puesta en marcha rápida

1. **Supabase**: crea un proyecto y ejecuta los archivos de `supabase/` en orden (`schema.sql`, `policies.sql`, opcional `seed.sql`).
2. **Backend**: ver [backend/README.md](backend/README.md).
3. **Web**: ver [web/README.md](web/README.md).

## Hosting recomendado
- **Frontend web** → Vercel
- **Backend FastAPI** → Railway o Render (Vercel no es ideal para procesos largos/ONVIF)
- **DB/Auth/Storage/Realtime** → Supabase
