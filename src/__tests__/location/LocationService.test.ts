/**
 * Tests for LocationService.getCurrentLocation — permission gate,
 * single read and fail-safe behaviour.
 *
 * Refs: Design §6.1; FR-1, FR-2, FR-3; AC-F11-1, AC-F11-2; DL-F11-02
 */

import {
  getCurrentPosition,
  requestPermission,
} from '../../services/location/_geolocationBackend';
import LocationService from '../../services/location/LocationService';

jest.mock('../../services/location/_geolocationBackend');

const mockRequest = requestPermission as jest.Mock;
const mockGetPosition = getCurrentPosition as jest.Mock;

describe('LocationService.getCurrentLocation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns coords when permission granted', async () => {
    mockRequest.mockResolvedValue('granted');
    mockGetPosition.mockResolvedValue({
      latitude: 10.776215,
      longitude: 106.695058,
    });

    const result = await LocationService.getCurrentLocation();

    expect(result).toEqual({
      latitude: 10.776215,
      longitude: 106.695058,
    });
  });

  it('returns null and skips read when permission denied', async () => {
    mockRequest.mockResolvedValue('denied');

    const result = await LocationService.getCurrentLocation();

    expect(result).toBeNull();
    expect(mockGetPosition).not.toHaveBeenCalled();
  });

  it('returns null on position error (fail-safe)', async () => {
    mockRequest.mockResolvedValue('granted');
    mockGetPosition.mockRejectedValue(new Error('gps timeout'));

    const result = await LocationService.getCurrentLocation();

    expect(result).toBeNull();
  });

  it('reads position only once', async () => {
    mockRequest.mockResolvedValue('granted');
    mockGetPosition.mockResolvedValue({ latitude: 1, longitude: 2 });

    await LocationService.getCurrentLocation();

    expect(mockGetPosition).toHaveBeenCalledTimes(1);
  });
});
