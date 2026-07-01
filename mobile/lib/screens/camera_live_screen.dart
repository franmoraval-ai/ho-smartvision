import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../config/env.dart';
import '../models/camera.dart';

/// Vista en vivo de una cámara mediante go2rtc (WebRTC/HLS dentro de un WebView).
///
/// El visor se carga desde `${STREAM_BASE_URL}/stream.html?src=<id>`. Configura
/// go2rtc en el gateway con un stream cuyo nombre coincida con el `id` de la
/// cámara (o ajusta aquí la convención de nombres).
class CameraLiveScreen extends StatefulWidget {
  const CameraLiveScreen({super.key, required this.camera});

  final Camera camera;

  @override
  State<CameraLiveScreen> createState() => _CameraLiveScreenState();
}

class _CameraLiveScreenState extends State<CameraLiveScreen> {
  WebViewController? _controller;
  bool _loading = true;

  String? get _streamUrl {
    if (Env.streamBaseUrl.isEmpty) return null;
    final base = Env.streamBaseUrl.replaceAll(RegExp(r'/+$'), '');
    return '$base/stream.html?src=${Uri.encodeComponent(widget.camera.id)}';
  }

  @override
  void initState() {
    super.initState();
    final url = _streamUrl;
    if (url != null) {
      _controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(Colors.black)
        ..setNavigationDelegate(
          NavigationDelegate(
            onPageFinished: (_) {
              if (mounted) setState(() => _loading = false);
            },
          ),
        )
        ..loadRequest(Uri.parse(url));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text(widget.camera.name)),
      body: _controller == null
          ? const _NoStreamConfigured()
          : Stack(
              children: [
                WebViewWidget(controller: _controller!),
                if (_loading)
                  const Center(child: CircularProgressIndicator()),
              ],
            ),
    );
  }
}

class _NoStreamConfigured extends StatelessWidget {
  const _NoStreamConfigured();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.live_tv_outlined, size: 56, color: Colors.white70),
            SizedBox(height: 12),
            Text(
              'Vista en vivo no configurada',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Text(
              'Define STREAM_BASE_URL (go2rtc) al compilar la app.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}
