import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/camera.dart';
import '../services/push_service.dart';
import '../services/supabase_service.dart';
import '../widgets/camera_card.dart';
import 'camera_live_screen.dart';
import 'events_screen.dart';
import 'share_access_screen.dart';

/// Pantalla principal con pestañas: Cámaras y Eventos.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final SupabaseService _service =
      SupabaseService(Supabase.instance.client);
  int _index = 0;

  @override
  void initState() {
    super.initState();
    // Registrar el dispositivo para notificaciones push (si Firebase está
    // configurado). Es idempotente y tolerante a fallos.
    PushService.init();
  }

  Future<void> _signOut() async {
    await PushService.removeToken();
    await _service.signOut();
  }

  Future<void> _openShare() async {
    final clientId = await _service.fetchMyClientId();
    if (!mounted) return;
    if (clientId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se encontró tu cuenta de cliente.')),
      );
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ShareAccessScreen(clientId: clientId),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      _CamerasTab(service: _service),
      EventsScreen(service: _service),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(_index == 0 ? 'Mis cámaras' : 'Eventos'),
        actions: [
          IconButton(
            tooltip: 'Compartir acceso',
            onPressed: _openShare,
            icon: const Icon(Icons.person_add_alt_1),
          ),
          IconButton(
            tooltip: 'Cerrar sesión',
            onPressed: _signOut,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.grid_view_rounded),
            label: 'Cámaras',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_rounded),
            label: 'Eventos',
          ),
        ],
      ),
    );
  }
}

/// Pestaña con el grid de cámaras.
class _CamerasTab extends StatefulWidget {
  const _CamerasTab({required this.service});

  final SupabaseService service;

  @override
  State<_CamerasTab> createState() => _CamerasTabState();
}

class _CamerasTabState extends State<_CamerasTab> {
  late Future<List<Camera>> _future = widget.service.fetchCameras();

  Future<void> _refresh() async {
    setState(() => _future = widget.service.fetchCameras());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<Camera>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _ErrorView(
              message: 'No se pudieron cargar las cámaras.',
              onRetry: _refresh,
            );
          }
          final cameras = snapshot.data ?? [];
          if (cameras.isEmpty) {
            return ListView(
              children: const [
                SizedBox(height: 120),
                Icon(Icons.videocam_off_outlined, size: 56),
                SizedBox(height: 12),
                Center(child: Text('Aún no tienes cámaras configuradas.')),
              ],
            );
          }
          return GridView.builder(
            padding: const EdgeInsets.all(12),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 0.95,
            ),
            itemCount: cameras.length,
            itemBuilder: (context, i) {
              final cam = cameras[i];
              return CameraCard(
                camera: cam,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => CameraLiveScreen(camera: cam),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, size: 48),
          const SizedBox(height: 12),
          Text(message),
          const SizedBox(height: 12),
          FilledButton.tonal(onPressed: onRetry, child: const Text('Reintentar')),
        ],
      ),
    );
  }
}
