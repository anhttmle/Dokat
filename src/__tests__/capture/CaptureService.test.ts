/**
 * Tests for CaptureService — validate → compress → build artifact.
 *
 * Refs: Design §6.3; FR-4, FR-8, FR-9; AC-F04-1, AC-F04-2, AC-F04-6
 */

import CaptureService from '../../services/capture/CaptureService';
import PetValidationService from '../../services/capture/PetValidationService';
import ImageCompressor from '../../services/capture/ImageCompressor';

jest.mock('../../services/capture/PetValidationService');
jest.mock('../../services/capture/ImageCompressor');

const mockValidate = PetValidationService.validate as jest.Mock;
const mockCompress = ImageCompressor.compress as jest.Mock;

describe('CaptureService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('skips compression and returns null when blocked', async () => {
    mockValidate.mockResolvedValue({
      humanConfidence: 0.95,
      allowed: false,
    });

    const result = await CaptureService.process(
      'file://raw.jpg',
      'user-1',
    );

    expect(result).toBeNull();
    expect(mockCompress).not.toHaveBeenCalled();
  });

  it('builds CapturedPhoto when valid', async () => {
    mockValidate.mockResolvedValue({
      humanConfidence: 0.1,
      allowed: true,
    });
    mockCompress.mockResolvedValue({
      uri: 'file://small.jpg',
      width: 1280,
      height: 720,
    });

    const result = await CaptureService.process(
      'file://raw.jpg',
      'user-1',
    );

    expect(result?.localUri).toBe('file://small.jpg');
    expect(result?.width).toBe(1280);
    expect(result?.height).toBe(720);
  });

  it('builds s3Key in posts/{userId}/{ts}_{uuid}.jpg format', async () => {
    mockValidate.mockResolvedValue({
      humanConfidence: 0.1,
      allowed: true,
    });
    mockCompress.mockResolvedValue({
      uri: 'file://small.jpg',
      width: 1280,
      height: 720,
    });

    const result = await CaptureService.process(
      'file://raw.jpg',
      'user-1',
    );

    expect(result?.s3Key).toMatch(/^posts\/user-1\/\d+_[0-9a-f-]+\.jpg$/);
  });

  it('returns null and does not throw on model error', async () => {
    mockValidate.mockRejectedValue(new Error('model failed'));

    const result = await CaptureService.process(
      'file://raw.jpg',
      'user-1',
    );

    expect(result).toBeNull();
  });

  it('sets 720p dimensions on the captured photo', async () => {
    mockValidate.mockResolvedValue({
      humanConfidence: 0.1,
      allowed: true,
    });
    mockCompress.mockResolvedValue({
      uri: 'file://small.jpg',
      width: 1280,
      height: 720,
    });

    const result = await CaptureService.process(
      'file://raw.jpg',
      'user-1',
    );

    expect(result?.width).toBe(1280);
    expect(result?.height).toBe(720);
  });
});
