/**
 * Manual Jest mock for ImageCompressor.
 *
 * Activated via
 * ``jest.mock('../../services/capture/ImageCompressor')``.
 * ``compress`` is a ``jest.fn()`` so tests can stub results.
 */

const ImageCompressor = {
  compress: jest.fn(),
};

export default ImageCompressor;
