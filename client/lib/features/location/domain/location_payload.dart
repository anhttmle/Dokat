/// Location metadata attached to a photo post (F11).
///
/// Stored only — not displayed to other users.
class LocationPayload {
  const LocationPayload({
    required this.latitude,
    required this.longitude,
    this.city,
    this.country,
  });

  final double latitude;
  final double longitude;
  final String? city;
  final String? country;

  Map<String, dynamic> toJson() => {
        'latitude': latitude,
        'longitude': longitude,
        if (city != null) 'city': city,
        if (country != null) 'country': country,
      };
}
