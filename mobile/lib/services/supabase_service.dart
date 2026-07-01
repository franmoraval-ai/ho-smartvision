import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/camera.dart';
import '../models/camera_event.dart';
import '../models/property.dart';

/// Acceso a datos vía Supabase (protegido por RLS según el `app_user`).
///
/// Las lecturas usan la sesión del usuario: las políticas RLS garantizan que
/// cada usuario solo vea las cámaras/eventos de su cliente.
class SupabaseService {
  SupabaseService(this._client);

  final SupabaseClient _client;

  SupabaseClient get client => _client;
  Session? get session => _client.auth.currentSession;
  User? get user => _client.auth.currentUser;

  Future<void> signIn(String email, String password) async {
    await _client.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> signOut() => _client.auth.signOut();

  /// Propiedades visibles para el usuario.
  Future<List<Property>> fetchProperties() async {
    final rows = await _client
        .from('properties')
        .select()
        .order('created_at', ascending: true);
    return (rows as List)
        .map((e) => Property.fromMap(e as Map<String, dynamic>))
        .toList();
  }

  /// Cámaras (vista pública sin credenciales). Filtrable por propiedad.
  Future<List<Camera>> fetchCameras({String? propertyId}) async {
    var query = _client.from('cameras_public').select();
    if (propertyId != null) {
      query = query.eq('property_id', propertyId);
    }
    final rows = await query.order('created_at', ascending: true);
    return (rows as List)
        .map((e) => Camera.fromMap(e as Map<String, dynamic>))
        .toList();
  }

  /// Eventos recientes, opcionalmente de una cámara concreta.
  Future<List<CameraEvent>> fetchEvents({String? cameraId, int limit = 50}) async {
    var query = _client.from('events').select();
    if (cameraId != null) {
      query = query.eq('camera_id', cameraId);
    }
    final rows = await query.order('timestamp', ascending: false).limit(limit);
    return (rows as List)
        .map((e) => CameraEvent.fromMap(e as Map<String, dynamic>))
        .toList();
  }

  /// El `client_id` del usuario actual (primer cliente vinculado).
  Future<String?> fetchMyClientId() async {
    final uid = user?.id;
    if (uid == null) return null;
    final row = await _client
        .from('app_users')
        .select('client_id')
        .eq('id', uid)
        .maybeSingle();
    return row?['client_id'] as String?;
  }
}
