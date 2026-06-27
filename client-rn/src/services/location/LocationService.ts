/**
 * LocationService — request location permission and read the device
 * coordinates once at send time (F11).
 *
 * Location is optional metadata: any permission or read failure
 * yields null so the photo send flow is never blocked (FR-3, §5).
 * Coordinates are read exactly once — no continuous tracking
 * (Technical Constraint). The native layer is injected via
 * _geolocationBackend so business logic can be tested in isolation.
 *
 * Refs: Design §1.1, §1.2, §2.1, §4.1, §5; FR-1, FR-2, FR-3;
 * AC-F11-1, AC-F11-2; DL-F11-02, DL-F11-03
 */

import {
  getCurrentPosition,
  requestPermission,
} from './_geolocationBackend';

export interface LocationMetadata {
  /** Device latitude at capture/send time, in [-90, 90]. */
  latitude: number;
  /** Device longitude at capture/send time, in [-180, 180]. */
  longitude: number;
}

const LocationService = {
  /**
   * Resolve the current location, or null when unavailable.
   *
   * Returns null when permission is not granted (without reading the
   * position) or when the position read fails (fail-safe).
   */
  getCurrentLocation: async (): Promise<LocationMetadata | null> => {
    try {
      const status = await requestPermission();
      if (status !== 'granted') {
        return null;
      }
      const position = await getCurrentPosition();
      return {
        latitude: position.latitude,
        longitude: position.longitude,
      };
    } catch {
      return null;
    }
  },
};

export default LocationService;
