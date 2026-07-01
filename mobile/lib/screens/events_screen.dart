import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:webview_flutter/webview_flutter.dart';

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
      return const _EventMeta(Icons.directions_walk, 'Persona', Color(0xFFEF4444));
    case 'motion':
      return const _EventMeta(Icons.motion_photos_on, 'Movimiento', Color(0xFF5B5BF6));
    case 'online':
      return const _EventMeta(Icons.wifi, 'Conectada', Color(0xFF16A34A));
    case 'offline':
      return const _EventMeta(Icons.wifi_off, 'Desconectada', Color(0xFF6B7280));
    default:
      return _EventMeta(Icons.sensors, type, const Color(0xFF06B6D4));
  }
}

/// Etiqueta legible para el encabezado del grupo de un día.
String _dayLabel(DateTime date) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final d = DateTime(date.year, date.month, date.day);
  final diff = today.difference(d).inDays;
  if (diff == 0) return 'Hoy';
  if (diff == 1) return 'Ayer';
  return DateFormat('EEEE d MMMM', 'es').format(date);
}

/// Elemento de la lista: cabecera de día o un evento.
sealed class _Row {
  const _Row();
}

class _HeaderRow extends _Row {
  const _HeaderRow(this.label, this.count);
  final String label;
  final int count;
}

class _EventRow extends _Row {
  const _EventRow(this.event);
  final CameraEvent event;
}

/// Línea de tiempo de eventos recientes (movimiento, persona, online…).
class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key, required this.service});

  final SupabaseService service;

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  late Future<List<CameraEvent>> _future = widget.service.fetchEvents();
  final _timeFmt = DateFormat('HH:mm');

  Future<void> _refresh() async {
    setState(() => _future = widget.service.fetchEvents());
    await _future;
  }

  /// Aplana los eventos en filas intercalando cabeceras de día.
  List<_Row> _buildRows(List<CameraEvent> events) {
    final rows = <_Row>[];
    final counts = <String, int>{};
    for (final e in events) {
      counts.update(_dayLabel(e.timestamp.toLocal()), (v) => v + 1,
          ifAbsent: () => 1);
    }
    String? currentDay;
    for (final e in events) {
      final label = _dayLabel(e.timestamp.toLocal());
      if (label != currentDay) {
        currentDay = label;
        rows.add(_HeaderRow(label, counts[label] ?? 0));
      }
      rows.add(_EventRow(e));
    }
    return rows;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<CameraEvent>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ListView(
              children: const [
                SizedBox(height: 120),
                Icon(Icons.error_outline, size: 48),
                SizedBox(height: 12),
                Center(child: Text('No se pudieron cargar los eventos.')),
              ],
            );
          }
          final events = snapshot.data ?? [];
          if (events.isEmpty) {
            return ListView(
              children: const [
                SizedBox(height: 120),
                Icon(Icons.notifications_off_outlined, size: 56),
                SizedBox(height: 12),
                Center(child: Text('No hay eventos recientes.')),
              ],
            );
          }
          final rows = _buildRows(events);
          return ListView.builder(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
            itemCount: rows.length,
            itemBuilder: (context, i) {
              final row = rows[i];
              if (row is _HeaderRow) {
                return _DayHeader(label: row.label, count: row.count);
              }
              return _EventTile(
                event: (row as _EventRow).event,
                timeFmt: _timeFmt,
              );
            },
          );
        },
      ),
    );
  }
}

class _DayHeader extends StatelessWidget {
  const _DayHeader({required this.label, required this.count});

  final String label;
  final int count;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 16, 4, 8),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: scheme.primary,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            label.toUpperCase(),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
              color: scheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            '· $count',
            style: TextStyle(fontSize: 12, color: scheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}

class _EventTile extends StatelessWidget {
  const _EventTile({required this.event, required this.timeFmt});

  final CameraEvent event;
  final DateFormat timeFmt;

  @override
  Widget build(BuildContext context) {
    final meta = _metaFor(event.eventType);
    final hasClip = event.videoClipUrl != null;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: hasClip
            ? () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => _ClipPlayerScreen(
                      url: event.videoClipUrl!,
                      title: meta.label,
                    ),
                  ),
                )
            : null,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            children: [
              _Thumbnail(url: event.thumbnailUrl, meta: meta),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(meta.icon, size: 16, color: meta.color),
                        const SizedBox(width: 6),
                        Text(
                          meta.label,
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            color: meta.color,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      timeFmt.format(event.timestamp.toLocal()),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              if (hasClip)
                Icon(Icons.play_circle_fill,
                    color: Theme.of(context).colorScheme.primary),
            ],
          ),
        ),
      ),
    );
  }
}

class _Thumbnail extends StatelessWidget {
  const _Thumbnail({required this.url, required this.meta});

  final String? url;
  final _EventMeta meta;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: SizedBox(
        width: 60,
        height: 60,
        child: url != null
            ? Image.network(
                url!,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => _fallback(),
                loadingBuilder: (context, child, progress) =>
                    progress == null ? child : _fallback(),
              )
            : _fallback(),
      ),
    );
  }

  Widget _fallback() {
    return DecoratedBox(
      decoration: BoxDecoration(color: meta.color.withValues(alpha: 0.15)),
      child: Center(child: Icon(meta.icon, color: meta.color)),
    );
  }
}

/// Reproductor de clip a pantalla completa (WebView sobre la URL del clip).
class _ClipPlayerScreen extends StatefulWidget {
  const _ClipPlayerScreen({required this.url, required this.title});

  final String url;
  final String title;

  @override
  State<_ClipPlayerScreen> createState() => _ClipPlayerScreenState();
}

class _ClipPlayerScreenState extends State<_ClipPlayerScreen> {
  late final WebViewController _controller = WebViewController()
    ..setJavaScriptMode(JavaScriptMode.unrestricted)
    ..setBackgroundColor(Colors.black)
    ..loadRequest(Uri.parse(widget.url));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text(widget.title)),
      body: WebViewWidget(controller: _controller),
    );
  }
}

