/**
 * ImageCompressor — compress a captured image to JPEG q80 at 720p.
 *
 * The actual native compression library (image-resizer /
 * expo-image-manipulator) is not yet a dependency, so the backend is
 * injectable and defaults to a no-op stub that echoes the target
 * dimensions (DL-F04-03). This keeps the compression contract
 * testable without a native module.
 *
 * Refs: Design §4.1; FR-2, FR-9; AC-F04-6; DL-F04-03
 */

/** JPEG quality applied before upload (FR-9). */
const JPEG_QUALITY = 0.8;
/** Target output width in pixels — 720p (FR-2). */
const TARGET_WIDTH = 1280;
/** Target output height in pixels — 720p (FR-2). */
const TARGET_HEIGHT = 720;

export interface CompressOptions {
  quality: number;
  maxWidth: number;
  maxHeight: number;
}

export interface CompressedImage {
  uri: string;
  width: number;
  height: number;
}

export type CompressBackend = (
  uri: string,
  options: CompressOptions,
) => Promise<CompressedImage>;

/**
 * Default backend stub used until a native compressor is integrated.
 *
 * Echoes the input URI at the requested target dimensions so the
 * orchestration flow can run end-to-end in tests (DL-F04-03).
 */
const defaultBackend: CompressBackend = async (uri, options) => ({
  uri,
  width: options.maxWidth,
  height: options.maxHeight,
});

const ImageCompressor = {
  /**
   * Compress an image to JPEG q80 at 720p.
   *
   * @param localUri - Local URI of the raw captured image.
   * @param backend - Injectable compression implementation.
   */
  compress: async (
    localUri: string,
    backend: CompressBackend = defaultBackend,
  ): Promise<CompressedImage> =>
    backend(localUri, {
      quality: JPEG_QUALITY,
      maxWidth: TARGET_WIDTH,
      maxHeight: TARGET_HEIGHT,
    }),
};

export default ImageCompressor;
