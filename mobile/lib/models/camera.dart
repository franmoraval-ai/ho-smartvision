/// Cámara tal y como la expone la vista `cameras_public` (sin credenciales).
class Camera {
  final String id;
  final String propertyId;
  final String? gatewayId;
  final String name;
  final String? rtspUrl;
  final bool isActive;
  final String provider;
  final String? providerDeviceSerial;
  final int providerChannel;

  const Camera({
    required this.id,
    required this.propertyId,
    required this.name,
    required this.isActive,
    this.gatewayId,
    this.rtspUrl,
    this.provider = 'local',
    this.providerDeviceSerial,
    this.providerChannel = 1,
  });

  bool get isCloud => provider != 'local';

  factory Camera.fromMap(Map<String, dynamic> map) => Camera(
        id: map['id'] as String,
        propertyId: map['property_id'] as String,
        gatewayId: map['gateway_id'] as String?,
        name: map['name'] as String,
        rtspUrl: map['rtsp_url'] as String?,
        isActive: (map['is_active'] as bool?) ?? false,
        provider: (map['provider'] as String?) ?? 'local',
        providerDeviceSerial: map['provider_device_serial'] as String?,
        providerChannel: (map['provider_channel'] as int?) ?? 1,
      );
}
