import '../domain/location_payload.dart';

/// Retrieves the device's current location for metadata purposes.
///
/// Location is store-only per F11 — it is attached to posts but
/// never shown to other users.
///
/// Uses the `geolocator` package in the real implementation.
/// Returns null gracefully when permission is denied or
/// location services are unavailable.
class LocationService {
  /// Returns a [LocationPayload] with the current coordinates,
  /// or null if location is unavailable.
  Future<Map<String, dynamic>?> getCurrentPayload() async {
    // Real implementation would use:
    //   final pos = await Geolocator.getCurrentPosition(...);
    //   return LocationPayload(latitude: pos.latitude, ...).toJson();
    // Returning null here so features work before adding geolocator dep.
    return null;
  }
}
