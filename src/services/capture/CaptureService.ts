/**
 * CaptureService — orchestrate validate → compress → build artifact.
 *
 * Runs human-detection validation first; only when the image is
 * allowed does it compress and build the CapturedPhoto handoff
 * artifact for F05. When blocked, it performs no compression and no
 * network I/O and returns null (AC-F04-2). Any model error is caught
 * and surfaced as null so the UI can offer a retake without crashing
 * (Design §5).
 *
 * Refs: Design §1.1, §1.2, §2.1, §4.1, §5; FR-4, FR-8, FR-9;
 *       AC-F04-1, AC-F04-2, AC-F04-6; DL-F04-01
 */

import PetValidationService from './PetValidationService';
import ImageCompressor from './ImageCompressor';

export interface CapturedPhoto {
  /** Local URI of the compressed image (JPEG q80, 1280×720). */
  localUri: string;
  /** Precomputed S3 key: posts/{userId}/{timestamp}_{uuid}.jpg */
  s3Key: string;
  /** Pixel width after compression (1280). */
  width: number;
  /** Pixel height after compression (720). */
  height: number;
  /** Capture time, ISO 8601 (post metadata in F05). */
  capturedAt: string;
}

/**
 * Generate a RFC 4122-style v4 UUID using Math.random.
 *
 * Avoids a native crypto dependency; the hex/hyphen output matches
 * the s3Key contract `posts/{userId}/{ts}_{uuid}.jpg` (AC-F04-6).
 */
function generateUuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(
    /[xy]/g,
    (char) => {
      const rand = (Math.random() * 16) | 0;
      const value = char === 'x' ? rand : (rand & 0x3) | 0x8;
      return value.toString(16);
    },
  );
}

/** Build the S3 object key for a user's captured photo (AC-F04-6). */
function buildS3Key(userId: string): string {
  return `posts/${userId}/${Date.now()}_${generateUuid()}.jpg`;
}

const CaptureService = {
  /**
   * Process a raw captured image into a CapturedPhoto artifact.
   *
   * @param localUri - Local URI of the raw 720p capture.
   * @param userId - Owner id, used to build the S3 key.
   * @returns CapturedPhoto when valid; null when blocked or on error.
   */
  process: async (
    localUri: string,
    userId: string,
  ): Promise<CapturedPhoto | null> => {
    try {
      const validation = await PetValidationService.validate(localUri);
      if (!validation.allowed) {
        return null;
      }
      const compressed = await ImageCompressor.compress(localUri);
      return {
        localUri: compressed.uri,
        s3Key: buildS3Key(userId),
        width: compressed.width,
        height: compressed.height,
        capturedAt: new Date().toISOString(),
      };
    } catch {
      return null;
    }
  },
};

export default CaptureService;
