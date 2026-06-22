/**
 * _geolocationBackend — injectable abstraction around the native
 * geolocation module (F11).
 *
 * Stub until a real geolocation library (e.g. expo-location /
 * @react-native-community/geolocation) is integrated (DL-F11-02).
 * Exported as named functions so LocationService can be exercised
 * with jest auto-mock, independently of the native layer.
 */

export type PermissionStatus = 'granted' | 'denied';

export interface DevicePosition {
  /** Device latitude at read time, in [-90, 90]. */
  latitude: number;
  /** Device longitude at read time, in [-180, 180]. */
  longitude: number;
}

/**
 * Request location permission from the OS.
 *
 * Stub: throws until the native library is wired in (DL-F11-02).
 */
export async function requestPermission(): Promise<PermissionStatus> {
  throw new Error('Native geolocation not integrated (DL-F11-02)');
}

/**
 * Read the current device position exactly once.
 *
 * Stub: throws until the native library is wired in (DL-F11-02).
 */
export async function getCurrentPosition(): Promise<DevicePosition> {
  throw new Error('Native geolocation not integrated (DL-F11-02)');
}
