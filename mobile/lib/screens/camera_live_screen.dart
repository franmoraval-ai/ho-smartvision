import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../config/env.dart';
import '../models/camera.dart';
import '../services/api_client.dart';

/// Vista en vivo de una cámara.
///
/// - Cámaras `local`: go2rtc dentro de un WebView
///   (`${STREAM_BASE_URL}/stream.html?src=<id>`).
/// - Cámaras cloud (ezviz/imou/reolink/tapo): el backend resuelve una URL fresca
///   en `/cameras/{id}/stream` y se reproduce HLS/FLV en un WebView.
class CameraLiveScreen extends StatefulWidget {
  const CameraLiveScreen({super.key, required this.camera});

  final Camera camera;

  @override
  State<CameraLiveScreen> createState() => _CameraLiveScreenState();
}

class _CameraLiveScreenState extends State<CameraLiveScreen> {
  WebViewController? _controller;
  bool _loading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      if (widget.camera.isCloud) {
        await _initCloud();
      } else {
        _initLocal();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  void _initLocal() {
    if (Env.streamBaseUrl.isEmpty) {
      setState(() => _loading = false);
      return;
    }
    final base = Env.streamBaseUrl.replaceAll(RegExp(r'/+$'), '');
    final url = '$base/stream.html?src=${Uri.encodeComponent(widget.camera.id)}';
    _controller = _buildController()..loadRequest(Uri.parse(url));
  }

  Future<void> _initCloud() async {
    final api = ApiClient(Supabase.instance.client.auth);
    final stream = await api.getCameraStream(widget.camera.id);
    if (!stream.browserPlayable) {
      setState(() {
        _loading = false;
        _errorMessage =
            'Las cámaras ${stream.provider} entregan ${stream.protocol.toUpperCase()}, '
            'que requiere un gateway (go2rtc) para reproducirse en la app.';
      });
      return;
    }
    _controller = _buildController()
      ..loadHtmlString(_playerHtml(stream.url, stream.protocol));
  }

  WebViewController _buildController() {
    return WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.black)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (_) {
            if (mounted) setState(() => _loading = false);
          },
        ),
      );
  }

  /// Página HTML mínima que reproduce HLS (hls.js) o FLV (mpegts.js).
  String _playerHtml(String url, String protocol) {
    final lib = protocol == 'flv'
        ? 'https://cdn.jsdelivr.net/npm/mpegts.js@1.7.3/dist/mpegts.js'
        : 'https://cdn.jsdelivr.net/npm/hls.js@1.5.17/dist/hls.min.js';
    final setup = protocol == 'flv'
        ? '''
          if (mpegts.isSupported()) {
            var p = mpegts.createPlayer({type:'flv', url:'$url'});
            p.attachMediaElement(v); p.load(); v.play();
          }'''
        : '''
          if (v.canPlayType('application/vnd.apple.mpegurl')) {
            v.src = '$url'; v.play();
          } else if (Hls.isSupported()) {
            var h = new Hls(); h.loadSource('$url'); h.attachMedia(v); v.play();
          }''';
    return '''
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;background:#000;height:100%}video{width:100%;height:100%;object-fit:contain}</style>
<script src="$lib"></script></head>
<body><video id="v" autoplay muted playsinline controls></video>
<script>var v=document.getElementById('v');$setup</script></body></html>''';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text(widget.camera.name)),
      body: _controller != null
          ? Stack(
              children: [
                WebViewWidget(controller: _controller!),
                if (_loading)
                  const Center(child: CircularProgressIndicator()),
              ],
            )
          : _errorMessage != null
              ? _LiveMessage(message: _errorMessage!)
              : const _NoStreamConfigured(),
    );
  }
}

class _LiveMessage extends StatelessWidget {
  const _LiveMessage({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.info_outline, size: 56, color: Colors.white70),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70),
            ),
          ],
        ),
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
              'Asigna un proveedor cloud a la cámara o define STREAM_BASE_URL (go2rtc).',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}
