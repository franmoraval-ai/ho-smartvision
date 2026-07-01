# Backend — Ho smartvision (FastAPI)

API en Python/FastAPI que centraliza autenticación, CRUD, descubrimiento ONVIF
e ingestión de eventos. Usa **supabase-py** con la `service_role key`.

## Requisitos
- Python 3.12+ (verificado también en 3.14; las dependencias usan rangos con
  wheels precompilados)
- Un proyecto de Supabase con el esquema aplicado (`../supabase/`)

## Configuración

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt        # rangos compatibles
# o, para versiones exactas reproducibles:
# pip install -r requirements.lock.txt
Copy-Item .env.example .env   # y rellena los valores
```

Genera la clave de cifrado Fernet y pégala en `.env` como `FERNET_KEY`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Ejecutar en desarrollo

```powershell
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Docs (OpenAPI/Swagger): http://localhost:8000/docs

## Endpoints principales

| Método | Ruta                 | Auth            | Descripción                          |
|--------|----------------------|-----------------|--------------------------------------|
| POST   | `/auth/login`        | público         | Login (email/contraseña) → JWT       |
| GET    | `/auth/me`           | Bearer          | Identidad del usuario actual         |
| CRUD   | `/clients`           | staff           | Clientes                             |
| CRUD   | `/properties`        | staff           | Propiedades                          |
| CRUD   | `/cameras`           | staff           | Cámaras (cifra credenciales ONVIF)   |
| CRUD   | `/gateways`          | staff           | Gateways Edge                        |
| GET    | `/events`            | staff           | Eventos recientes                    |
| POST   | `/events/ingest`     | `X-Gateway-Key` | Ingestión desde el Gateway Edge      |
| GET    | `/discover-onvif`    | staff           | Descubrimiento ONVIF (real/simulado) |
| CRUD   | `/app-users`         | staff           | Usuarios de la app móvil             |

## Seguridad
- Los JWT de Supabase se validan con `SUPABASE_JWT_SECRET` (HS256).
- El acceso de "staff" se comprueba contra la tabla `staff`.
- Las contraseñas ONVIF se cifran con Fernet (`FERNET_KEY`) y nunca se devuelven.
- El Gateway Edge se autentica con `X-Gateway-Key` (`GATEWAY_API_KEY`).

## Despliegue (Railway / Render)
- Usa el `Dockerfile` incluido (base `python:3.12-slim`).
- **Render:** importa `render.yaml` (New > Blueprint) y rellena los secretos.
- **Railway:** el repo incluye `railway.json` (build con Dockerfile + healthcheck).
- Define todas las variables de `.env.example` en el panel del proveedor.
- El healthcheck está en `/health`.

## Verificación local rápida
```powershell
# Tras configurar .env, comprueba que la app arranca:
uvicorn app.main:app --reload
# y en otra terminal:
curl http://localhost:8000/health   # -> {"status":"ok",...}
```
