# App móvil — Ho smartvision (Flutter)

App para clientes (residenciales y comercios) para ver y gestionar sus cámaras.
Pensada para ser **muy simple y bonita** para usuarios no técnicos.

## Funcionalidades
- **Login** con Supabase Auth (email/contraseña).
- **Grid de cámaras** con estado (en vivo / offline).
- **Vista en vivo** vía go2rtc (WebRTC/HLS) dentro de un WebView.
- **Eventos** recientes (movimiento, persona, online…).
- **Compartir acceso**: un `owner` invita a familiares/visores.

## Arquitectura
- **Auth y datos**: `supabase_flutter` directo contra Supabase. Las políticas
  **RLS** garantizan que cada usuario solo vea los datos de su cliente.
  - Cámaras: se leen de la vista `cameras_public` (sin credenciales ONVIF).
  - Eventos/propiedades: tablas `events` / `properties` filtradas por RLS.
- **Acciones privilegiadas** (invitar usuarios): backend FastAPI
  (`POST /app-users/invite`) con el JWT del usuario.
- **Streaming**: go2rtc en el gateway; el visor se abre en
  `${STREAM_BASE_URL}/stream.html?src=<id_camara>`.

## Requisitos
- Flutter 3.35+ (Dart 3.9+).

## Ejecutar

```bash
cd mobile
flutter pub get
flutter run \
  --dart-define=SUPABASE_URL=https://xxxx.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=eyJ... \
  --dart-define=BACKEND_URL=https://ho-smartvision-api.onrender.com \
  --dart-define=STREAM_BASE_URL=https://stream.tudominio.com
```

> Sugerencia: crea un `run.json`/launch config o un script para no repetir los
> `--dart-define`. Nunca incluyas la `service_role` key en la app.

## Configuración con archivo (recomendado)

En lugar de repetir los `--dart-define`, usa un archivo JSON:

```bash
cd mobile
cp dart_defines.example.json dart_defines.json   # rellena tus valores reales
flutter run --dart-define-from-file=dart_defines.json
```

`dart_defines.json` está en `.gitignore` (no se versiona).

## Compilar release para Android

1. **Genera un keystore de firma** (una sola vez):
   ```bash
   cd mobile/android
   keytool -genkey -v -keystore upload-keystore.jks -storetype JKS \
     -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
2. **Crea `key.properties`** a partir de la plantilla y rellena las contraseñas:
   ```bash
   cp key.properties.example key.properties
   ```
3. **Compila** el APK o el App Bundle firmado:
   ```bash
   cd ..
   flutter build apk --release --dart-define-from-file=dart_defines.json      # APK (instalar en teléfono)
   flutter build appbundle --release --dart-define-from-file=dart_defines.json # AAB (Play Store)
   ```

El artefacto queda en `build/app/outputs/`. Si no existe `key.properties`, el
build usa la firma *debug* (solo válido para pruebas, no para Play Store).

## Estructura
```
lib/
  main.dart                 # init Supabase + enrutado por sesión
  config/                   # env (dart-define) y tema
  models/                   # Camera, CameraEvent, Property
  services/                 # SupabaseService (RLS) + ApiClient (backend)
  screens/                  # login, home, live, events, share
  widgets/                  # CameraCard
```

## Notas de streaming
go2rtc publica cada stream con un nombre. Para que la vista en vivo funcione,
el nombre del stream debe coincidir con el `id` de la cámara, o ajusta la
convención en `screens/camera_live_screen.dart`. Expón go2rtc tras HTTPS
(reverse proxy) para `STREAM_BASE_URL`.
