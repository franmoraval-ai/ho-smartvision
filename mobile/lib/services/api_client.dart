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
}
