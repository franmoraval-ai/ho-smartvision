import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../config/env.dart';

/// Cliente del backend FastAPI para acciones privilegiadas (invitar usuarios).
///
/// Adjunta el JWT de Supabase de la sesión actual como `Authorization: Bearer`.
class ApiClient {
  ApiClient(this._auth);

  final GoTrueClient _auth;

  Map<String, String> get _headers {
    final token = _auth.currentSession?.accessToken;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Invita a un usuario al cliente indicado (solo owners/staff en el backend).
  Future<void> inviteUser({
    required String email,
    required String password,
    required String clientId,
    required String role, // 'family' | 'viewer' | 'owner'
  }) async {
    final res = await http.post(
      Uri.parse('${Env.backendUrl}/app-users/invite'),
      headers: _headers,
      body: jsonEncode({
        'email': email,
        'password': password,
        'client_id': clientId,
        'role': role,
      }),
    );
    if (res.statusCode >= 400) {
      String detail = 'Error ${res.statusCode}';
      try {
        detail = (jsonDecode(res.body)['detail'] ?? detail).toString();
      } catch (_) {}
      throw Exception(detail);
    }
  }

  /// Resuelve la URL de reproducción en vivo de una cámara cloud/directo.
  Future<CameraStream> getCameraStream(String cameraId) async {
    final res = await http.get(
      Uri.parse('${Env.backendUrl}/cameras/$cameraId/stream'),
      headers: _headers,
    );
    if (res.statusCode >= 400) {
      String detail = 'Error ${res.statusCode}';
      try {
        detail = (jsonDecode(res.body)['detail'] ?? detail).toString();
      } catch (_) {}
      throw Exception(detail);
    }
    return CameraStream.fromMap(jsonDecode(res.body) as Map<String, dynamic>);
  }
}

/// URL de reproducción en vivo devuelta por el backend.
class CameraStream {
  final String url;
  final String protocol; // hls | flv | rtmp | rtsp
  final String provider;
  final bool cloud;
  final bool browserPlayable;

  const CameraStream({
    required this.url,
    required this.protocol,
    required this.provider,
    required this.cloud,
    required this.browserPlayable,
  });

  factory CameraStream.fromMap(Map<String, dynamic> map) => CameraStream(
        url: map['url'] as String,
        protocol: map['protocol'] as String,
        provider: map['provider'] as String,
        cloud: (map['cloud'] as bool?) ?? false,
        browserPlayable: (map['browser_playable'] as bool?) ?? false,
      );
}
