import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// Handler de mensajes en segundo plano (app cerrada/background).
///
/// Debe ser una función top-level (no un método) y estar anotada para que
/// sobreviva al tree-shaking. El SO muestra automáticamente las notificaciones
/// de tipo `notification`; aquí solo registramos por si llega `data`.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // No hace falta inicializar Firebase aquí para notificaciones simples.
  debugPrint('Push en background: ${message.messageId}');
}

/// Gestiona las notificaciones push nativas (Firebase Cloud Messaging).
///
/// Es tolerante a fallos: si Firebase no está configurado (sin
/// `google-services.json` / plist), NO rompe el arranque de la app.
class PushService {
  const PushService._();

  static bool _initialized = false;

  /// Inicializa Firebase + FCM y registra el token del dispositivo en Supabase.
  /// Llamar tras el login (cuando ya hay sesión de Supabase).
  static Future<void> init() async {
    if (_initialized) return;
    try {
      await Firebase.initializeApp();
      FirebaseMessaging.onBackgroundMessage(
        firebaseMessagingBackgroundHandler,
      );

      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission();
      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        return;
      }

      // iOS: asegurar presentación en primer plano.
      await messaging.setForegroundNotificationPresentationOptions(
        alert: true,
        badge: true,
        sound: true,
      );

      final token = await messaging.getToken();
      if (token != null) await _saveToken(token);

      // Guardar también si el token se renueva.
      messaging.onTokenRefresh.listen(_saveToken);

      _initialized = true;
    } catch (e) {
      debugPrint('FCM no disponible (¿Firebase sin configurar?): $e');
    }
  }

  /// Guarda/actualiza el token FCM del usuario actual en `device_tokens`.
  static Future<void> _saveToken(String token) async {
    final client = Supabase.instance.client;
    final user = client.auth.currentUser;
    if (user == null) return;

    try {
      await client.from('device_tokens').upsert(
        {
          'user_id': user.id,
          'fcm_token': token,
          'platform': defaultTargetPlatform == TargetPlatform.iOS
              ? 'ios'
              : 'android',
        },
        onConflict: 'fcm_token',
      );
    } catch (e) {
      debugPrint('No se pudo guardar el token FCM: $e');
    }
  }

  /// Elimina el token del dispositivo actual (llamar al cerrar sesión).
  static Future<void> removeToken() async {
    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null) return;
      await Supabase.instance.client
          .from('device_tokens')
          .delete()
          .eq('fcm_token', token);
    } catch (e) {
      debugPrint('No se pudo eliminar el token FCM: $e');
    }
  }
}
