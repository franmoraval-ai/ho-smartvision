# Gateway Edge — Ho smartvision (Raspberry Pi)

Script Python que corre en la red local del cliente (Raspberry Pi) y:

1. **Heartbeat** periódico al backend → mantiene `gateways.last_seen`.
2. **Descubre cámaras ONVIF** (WS-Discovery) y obtiene sus URIs RTSP.
3. **Configura go2rtc** para reexponer las cámaras como WebRTC/HLS de baja
   latencia (consumible por la app móvil y el panel web).
4. **Reenvía eventos** al backend (`POST /events/ingest`) autenticado por
   `X-Gateway-Key`.

## Arquitectura

```
Cámaras ONVIF/RTSP ──┐
                     ├─► [ Raspberry Pi ]
                     │      ├─ go2rtc        (RTSP → WebRTC/HLS, puertos 1984/8554/8555)
                     │      └─ main.py       (descubrimiento + heartbeat + eventos)
                     │             │ HTTPS (X-Gateway-Key)
                     └─────────────┴────────► Backend FastAPI ─► Supabase
```

## Requisitos
- Raspberry Pi OS (64-bit recomendado) o cualquier Linux ARM/x86.
- Python 3.11+.
- El `device_id` debe estar registrado en la tabla `gateways` desde el panel web.

## Instalación rápida (Raspberry Pi)

```bash
git clone <repo> && cd ho-smartvision/gateway
cp .env.example .env   # edita tus valores
sudo bash install.sh   # instala go2rtc + servicios systemd
sudo systemctl restart ho-smartvision-gateway
journalctl -u ho-smartvision-gateway -f
```

## Ejecución manual (desarrollo)

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # edita tus valores
python main.py
```

## Variables de entorno
Ver [`.env.example`](.env.example). Las obligatorias son `GATEWAY_DEVICE_ID`,
`BACKEND_URL` y `GATEWAY_API_KEY`.

## Streams de go2rtc
Cada cámara descubierta se publica con la clave `cam_<ip_con_guiones_bajos>`.
Ejemplos de consumo:

- WebRTC (app/web): `http://<pi>:1984/api/ws?src=cam_192_168_1_50`
- HLS:              `http://<pi>:1984/api/stream.m3u8?src=cam_192_168_1_50`
- RTSP:            `rtsp://<pi>:8554/cam_192_168_1_50`

## Seguridad
- El gateway nunca recibe credenciales de cámara desde el backend; usa las
  `ONVIF_USERNAME`/`ONVIF_PASSWORD` locales para descubrir RTSP.
- Toda comunicación con el backend va firmada con `X-Gateway-Key`.
- Mantén la Raspberry Pi en una VLAN aislada siempre que sea posible.

## Eventos
El bucle emite un evento `online` por cada cámara descubierta y mapeada a un
`camera_id` del backend. Para detección de movimiento/persona reales, intégralo
con el PullPoint ONVIF de la cámara o con un detector (p. ej. Frigate) y llama a
`BackendClient.ingest_event(...)`.
