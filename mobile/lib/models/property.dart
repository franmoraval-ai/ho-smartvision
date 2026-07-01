/// Propiedad (ubicación física) del cliente.
class Property {
  final String id;
  final String clientId;
  final String name;
  final String? address;

  const Property({
    required this.id,
    required this.clientId,
    required this.name,
    this.address,
  });

  factory Property.fromMap(Map<String, dynamic> map) => Property(
        id: map['id'] as String,
        clientId: map['client_id'] as String,
        name: map['name'] as String,
        address: map['address'] as String?,
      );
}
