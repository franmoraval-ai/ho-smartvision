/// Configuración leída en tiempo de compilación con `--dart-define`.
///
/// Ejemplo de ejecución:
/// ```bash
/// flutter run \
///   --dart-define=SUPABASE_URL=https://xxxx.supabase.co \
///   --dart-define=SUPABASE_ANON_KEY=eyJ... \
///   --dart-define=BACKEND_URL=https://ho-smartvision-api.onrender.com
/// ```
class Env {
  const Env._();

  static const String supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const String supabaseAnonKey =
      String.fromEnvironment('SUPABASE_ANON_KEY');

  /// URL del backend FastAPI (para invitar usuarios / acciones privilegiadas).
  static const String backendUrl = String.fromEnvironment('BACKEND_URL');

  /// Base pública de go2rtc para la vista en vivo (p. ej. https://stream.tudominio.com).
  /// El visor se abre en `${streamBaseUrl}/stream.html?src=<nombre_stream>`.
  static const String streamBaseUrl = String.fromEnvironment('STREAM_BASE_URL');

  /// Valida que la configuración mínima esté presente.
  static bool get isConfigured =>
      supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
}
