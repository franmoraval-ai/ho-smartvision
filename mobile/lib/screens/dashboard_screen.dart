import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../config/theme.dart';
import '../models/camera.dart';
import '../models/camera_event.dart';
import '../services/supabase_service.dart';

/// Metadatos visuales por tipo de evento (icono, etiqueta y color).
class _EventMeta {
  const _EventMeta(this.icon, this.label, this.color);
  final IconData icon;
  final String label;
  final Color color;
}

_EventMeta _metaFor(String type) {
  switch (type) {
    case 'person':
      return const _EventMeta(
          Icons.directions_walk, 'Persona', Color(0xFFEF4444));
    case 'motion':
      return const _EventMeta(
          Icons.motion_photos_on, 'Movimiento', Color(0xFF5B5BF6));
    case 'online':
      return const _EventMeta(Icons.wifi, 'Conectada', Color(0xFF16A34A));
    case 'offline':
      return const _EventMeta(
          Icons.wifi_off, 'Desconectada', Color(0xFF6B7280));
    default:
      return _EventMeta(Icons.sensors, type, const Color(0xFF06B6D4));
  }
}

/// Resumen de datos para el dashboard.
class _Summary {
  const _Summary({required this.cameras, required this.events});
  final List<Camera> cameras;
  final List<CameraEvent> events;

  int get totalCameras => cameras.length;
  int get activeCameras => cameras.where((c) => c.isActive).length;

  int get eventsToday {
    final now = DateTime.now();
    final start = DateTime(now.year, now.month, now.day);
    return events
        .where((e) => e.timestamp.toLocal().isAfter(start))
        .length;
  }
}

/// Pestaña de Inicio: saludo, tarjetas de resumen y eventos recientes.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    required this.service,
    required this.onSeeCameras,
    required this.onSeeEvents,
    required this.onShare,
  });

  final SupabaseService service;
  final VoidCallback onSeeCameras;
  final VoidCallback onSeeEvents;
  final VoidCallback onShare;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<_Summary> _future = _load();
  final _timeFmt = DateFormat('HH:mm');

  Future<_Summary> _load() async {
    final results = await Future.wait([
      widget.service.fetchCameras(),
      widget.service.fetchEvents(limit: 20),
    ]);
    return _Summary(
      cameras: results[0] as List<Camera>,
      events: results[1] as List<CameraEvent>,
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<_Summary>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final summary = snapshot.data;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
            children: [
              _Header(email: widget.service.user?.email),
              const SizedBox(height: 20),
              if (snapshot.hasError)
                _InlineError(onRetry: _refresh)
              else if (summary != null) ...[
                _StatsRow(
                  summary: summary,
                  onCameras: widget.onSeeCameras,
                  onEvents: widget.onSeeEvents,
                ),
                const SizedBox(height: 24),
                _QuickActions(
                  onSeeCameras: widget.onSeeCameras,
                  onSeeEvents: widget.onSeeEvents,
                  onShare: widget.onShare,
                ),
                const SizedBox(height: 24),
                _RecentEvents(
                  events: summary.events.take(4).toList(),
                  timeFmt: _timeFmt,
                  onSeeAll: widget.onSeeEvents,
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({this.email});

  final String? email;

  @override
  Widget build(BuildContext context) {
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Buenos días'
        : (hour < 19 ? 'Buenas tardes' : 'Buenas noches');
    final name = (email ?? '').split('@').first;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AppTheme.brandLinearGradient,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            greeting,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            name.isEmpty ? 'Bienvenido' : name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: const [
              Icon(Icons.shield_outlined, color: Colors.white70, size: 18),
              SizedBox(width: 6),
              Text(
                'Tu hogar, siempre vigilado',
                style: TextStyle(color: Colors.white70, fontSize: 13),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  const _StatsRow({
    required this.summary,
    required this.onCameras,
    required this.onEvents,
  });

  final _Summary summary;
  final VoidCallback onCameras;
  final VoidCallback onEvents;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _StatCard(
            icon: Icons.videocam_rounded,
            value: '${summary.totalCameras}',
            label: 'Cámaras',
            color: const Color(0xFF5B5BF6),
            onTap: onCameras,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _StatCard(
            icon: Icons.check_circle_rounded,
            value: '${summary.activeCameras}',
            label: 'Activas',
            color: const Color(0xFF16A34A),
            onTap: onCameras,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _StatCard(
            icon: Icons.notifications_active_rounded,
            value: '${summary.eventsToday}',
            label: 'Hoy',
            color: const Color(0xFF06B6D4),
            onTap: onEvents,
          ),
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String value;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 10),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(height: 10),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                ),
              ),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  const _QuickActions({
    required this.onSeeCameras,
    required this.onSeeEvents,
    required this.onShare,
  });

  final VoidCallback onSeeCameras;
  final VoidCallback onSeeEvents;
  final VoidCallback onShare;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle('Accesos rápidos'),
        const SizedBox(height: 8),
        Card(
          margin: EdgeInsets.zero,
          child: Column(
            children: [
              _ActionTile(
                icon: Icons.grid_view_rounded,
                title: 'Ver mis cámaras',
                subtitle: 'Vista en vivo de tus cámaras',
                onTap: onSeeCameras,
              ),
              const Divider(height: 1),
              _ActionTile(
                icon: Icons.notifications_rounded,
                title: 'Eventos recientes',
                subtitle: 'Movimiento, personas y estado',
                onTap: onSeeEvents,
              ),
              const Divider(height: 1),
              _ActionTile(
                icon: Icons.person_add_alt_1_rounded,
                title: 'Compartir acceso',
                subtitle: 'Invita a familiares o vigilantes',
                onTap: onShare,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListTile(
      onTap: onTap,
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: scheme.primaryContainer,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: scheme.onPrimaryContainer, size: 22),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right_rounded),
    );
  }
}

class _RecentEvents extends StatelessWidget {
  const _RecentEvents({
    required this.events,
    required this.timeFmt,
    required this.onSeeAll,
  });

  final List<CameraEvent> events;
  final DateFormat timeFmt;
  final VoidCallback onSeeAll;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const _SectionTitle('Actividad reciente'),
            TextButton(onPressed: onSeeAll, child: const Text('Ver todo')),
          ],
        ),
        const SizedBox(height: 4),
        if (events.isEmpty)
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Icon(
                    Icons.notifications_off_outlined,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text('Sin actividad reciente por ahora.'),
                  ),
                ],
              ),
            ),
          )
        else
          Card(
            margin: EdgeInsets.zero,
            child: Column(
              children: [
                for (var i = 0; i < events.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  _RecentEventTile(event: events[i], timeFmt: timeFmt),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _RecentEventTile extends StatelessWidget {
  const _RecentEventTile({required this.event, required this.timeFmt});

  final CameraEvent event;
  final DateFormat timeFmt;

  @override
  Widget build(BuildContext context) {
    final meta = _metaFor(event.eventType);
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: meta.color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(meta.icon, color: meta.color, size: 22),
      ),
      title: Text(meta.label,
          style: const TextStyle(fontWeight: FontWeight.w600)),
      subtitle: Text(_relativeDay(event.timestamp.toLocal())),
      trailing: Text(
        timeFmt.format(event.timestamp.toLocal()),
        style: TextStyle(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  String _relativeDay(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(date.year, date.month, date.day);
    final diff = today.difference(d).inDays;
    if (diff == 0) return 'Hoy';
    if (diff == 1) return 'Ayer';
    return DateFormat('d MMM', 'es').format(date);
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
    );
  }
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 40),
            const SizedBox(height: 12),
            const Text('No se pudo cargar tu resumen.'),
            const SizedBox(height: 12),
            FilledButton.tonal(
              onPressed: onRetry,
              child: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}
