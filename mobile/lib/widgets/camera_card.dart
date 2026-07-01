import 'dart:async';

import 'package:flutter/material.dart';

import '../config/env.dart';
import '../models/camera.dart';

/// Tarjeta de cámara para el grid del Home.
///
/// Muestra una miniatura tipo Ring tomada de go2rtc
/// (`${STREAM_BASE_URL}/api/frame.jpeg?src=<id>`) que se refresca cada
/// [refreshInterval]. Si no hay stream o falla la carga, muestra un
/// marcador de posición con degradado.
class CameraCard extends StatefulWidget {
  const CameraCard({
    super.key,
    required this.camera,
    required this.onTap,
    this.refreshInterval = const Duration(seconds: 10),
  });

  final Camera camera;
  final VoidCallback onTap;
  final Duration refreshInterval;

  @override
  State<CameraCard> createState() => _CameraCardState();
}

class _CameraCardState extends State<CameraCard> {
  Timer? _timer;
  int _cacheBuster = DateTime.now().millisecondsSinceEpoch;
  bool _failed = false;

  bool get _canSnapshot =>
      widget.camera.isActive && Env.streamBaseUrl.isNotEmpty;

  String get _snapshotUrl {
    final base = Env.streamBaseUrl.replaceAll(RegExp(r'/+$'), '');
    return '$base/api/frame.jpeg?src=${Uri.encodeComponent(widget.camera.id)}'
        '&t=$_cacheBuster';
  }

  @override
  void initState() {
    super.initState();
    if (_canSnapshot) {
      _timer = Timer.periodic(widget.refreshInterval, (_) {
        if (!mounted) return;
        setState(() {
          _failed = false; // reintentar en cada ciclo (cold start de go2rtc)
          _cacheBuster = DateTime.now().millisecondsSinceEpoch;
        });
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: widget.onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  _buildPreview(scheme),
                  Positioned(
                    top: 8,
                    left: 8,
                    child: _StatusBadge(active: widget.camera.isActive),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(10),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.camera.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  Icon(Icons.play_circle_fill, size: 22, color: scheme.primary),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreview(ColorScheme scheme) {
    if (_canSnapshot && !_failed) {
      return Image.network(
        _snapshotUrl,
        key: ValueKey(_cacheBuster),
        fit: BoxFit.cover,
        gaplessPlayback: true,
        errorBuilder: (context, error, stack) {
          // No fallar de forma permanente: el próximo tick reintenta.
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) setState(() => _failed = true);
          });
          return _placeholder(scheme);
        },
        loadingBuilder: (context, child, progress) {
          if (progress == null) return child;
          return _placeholder(scheme, loading: true);
        },
      );
    }
    return _placeholder(scheme);
  }

  Widget _placeholder(ColorScheme scheme, {bool loading = false}) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            scheme.surfaceContainerHighest,
            scheme.surfaceContainerHigh,
          ],
        ),
      ),
      child: Center(
        child: loading
            ? const SizedBox(
                width: 26,
                height: 26,
                child: CircularProgressIndicator(strokeWidth: 2.5),
              )
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    widget.camera.isActive
                        ? Icons.photo_camera_outlined
                        : Icons.videocam_off_rounded,
                    size: 34,
                    color: scheme.onSurfaceVariant,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    widget.camera.isActive ? 'Sin vista previa' : 'Inactiva',
                    style: TextStyle(
                      fontSize: 11,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) {
    final Color color = active ? Colors.redAccent : Colors.grey;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            active ? 'EN VIVO' : 'OFFLINE',
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}
