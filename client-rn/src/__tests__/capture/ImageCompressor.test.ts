/**
 * Tests for ImageCompressor — JPEG q80 at 720p.
 *
 * Refs: Design §6.2; FR-2, FR-9; AC-F04-6; DL-F04-03
 */

import ImageCompressor from '../../services/capture/ImageCompressor';

describe('ImageCompressor', () => {
  it('compresses with JPEG quality 0.8', async () => {
    const backend = jest.fn().mockResolvedValue({
      uri: 'file://out.jpg',
      width: 1280,
      height: 720,
    });

    const result = await ImageCompressor.compress(
      'file://in.jpg',
      backend,
    );

    expect(backend).toHaveBeenCalledWith(
      'file://in.jpg',
      expect.objectContaining({
        quality: 0.8,
        maxWidth: 1280,
        maxHeight: 720,
      }),
    );
    expect(result.uri).toBe('file://out.jpg');
  });

  it('targets 720p output dimensions', async () => {
    const backend = jest.fn().mockResolvedValue({
      uri: 'file://out.jpg',
      width: 1280,
      height: 720,
    });

    const result = await ImageCompressor.compress(
      'file://in.jpg',
      backend,
    );

    expect(result.width).toBe(1280);
    expect(result.height).toBe(720);
  });

  it('returns a new JPEG URI', async () => {
    const backend = jest.fn().mockResolvedValue({
      uri: 'file://out.jpg',
      width: 1280,
      height: 720,
    });

    const result = await ImageCompressor.compress(
      'file://in.jpg',
      backend,
    );

    expect(result.uri).toMatch(/\.jpg$/);
  });
});
