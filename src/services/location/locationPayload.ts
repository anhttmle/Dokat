/**
 * locationPayload — map LocationMetadata into the optional fields
 * merged onto the POST /posts request body (F11).
 *
 * Coordinates are passed through unchanged to preserve full GPS
 * precision (Technical Constraint). When no location is available the
 * builder omits both fields entirely so the backend stores NULL
 * (AC-F11-2).
 *
 * Refs: Design §1.1, §1.2, §2.2, §3.1, §4.1; FR-3, FR-4;
 * AC-F11-1, AC-F11-2
 */

import type { LocationMetadata } from './LocationService';

export interface LocationPayload {
  /** Present only when coordinates were resolved. */
  latitude?: number;
  longitude?: number;
}

/**
 * Build the location portion of the POST /posts body.
 *
 * @param loc - Resolved metadata, or null when unavailable.
 * @returns Coordinate fields, or an empty object when loc is null.
 */
export function buildLocationPayload(
  loc: LocationMetadata | null,
): LocationPayload {
  if (loc === null) {
    return {};
  }
  return { latitude: loc.latitude, longitude: loc.longitude };
}
