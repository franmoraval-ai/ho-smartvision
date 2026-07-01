/// Evento detectado por una cámara (movimiento, persona, online…).
class CameraEvent {
  final String id;
  final String cameraId;
  final String eventType;
  final DateTime timestamp;
  final String? thumbnailUrl;
  final String? videoClipUrl;
  final Map<String, dynamic> metadata;

  const CameraEvent({
    required this.id,
    required this.cameraId,
    required this.eventType,
    required this.timestamp,
    this.thumbnailUrl,
    this.videoClipUrl,
    this.metadata = const {},
  });

  factory CameraEvent.fromMap(Map<String, dynamic> map) => CameraEvent(
        id: map['id'] as String,
        cameraId: map['camera_id'] as String,
        eventType: map['event_type'] as String,
        timestamp: DateTime.parse(map['timestamp'] as String),
        thumbnailUrl: map['thumbnail_url'] as String?,
        videoClipUrl: map['video_clip_url'] as String?,
        metadata: (map['metadata'] as Map?)?.cast<String, dynamic>() ?? const {},
      );
}
