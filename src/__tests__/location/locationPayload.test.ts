/**
 * Tests for buildLocationPayload — mapping LocationMetadata into the
 * POST /posts body fields.
 *
 * Refs: Design §6.2; FR-3, FR-4; AC-F11-1, AC-F11-2
 */

import { buildLocationPayload } from '../../services/location/locationPayload';

describe('buildLocationPayload', () => {
  it('includes coords when location present', () => {
    const payload = buildLocationPayload({
      latitude: 10.776215,
      longitude: 106.695058,
    });

    expect(payload).toEqual({
      latitude: 10.776215,
      longitude: 106.695058,
    });
  });

  it('returns empty object when location is null', () => {
    expect(buildLocationPayload(null)).toEqual({});
  });

  it('preserves full coordinate precision', () => {
    const payload = buildLocationPayload({
      latitude: 10.12345678,
      longitude: 106.87654321,
    });

    expect(payload.latitude).toBe(10.12345678);
    expect(payload.longitude).toBe(106.87654321);
  });
});
