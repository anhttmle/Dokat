/**
 * PetValidationService — on-device human-detection gate (F04).
 *
 * Runs the validation model and applies HUMAN_BLOCK_THRESHOLD to
 * decide whether an image may proceed. A high human confidence blocks
 * the image (FR-4); low confidence is allowed to prioritise UX
 * (FR-5). The model runner is injected via _validationModelStub so it
 * can be mocked in tests independently.
 *
 * Refs: Design §2.2, §2.4, §4.1; FR-3, FR-4, FR-5; AC-F04-2, AC-F04-3
 */

import { runValidationModel } from '../ai/_validationModelStub';

/** Block threshold for human detection (FR-4, DL-F04-02). */
export const HUMAN_BLOCK_THRESHOLD = 0.7;

export interface ValidationResult {
  /** Confidence that a human is present, in [0, 1]. */
  humanConfidence: number;
  /**
   * true if the image may be uploaded.
   * false when humanConfidence >= HUMAN_BLOCK_THRESHOLD (FR-4);
   * low confidence yields true (FR-5, UX priority).
   */
  allowed: boolean;
}

const PetValidationService = {
  /**
   * Validate that an image does not clearly contain a human.
   *
   * @param localUri - Local URI of the captured image.
   */
  validate: async (localUri: string): Promise<ValidationResult> => {
    const raw = await runValidationModel(localUri);
    return {
      humanConfidence: raw.human_confidence,
      allowed: raw.human_confidence < HUMAN_BLOCK_THRESHOLD,
    };
  },
};

export default PetValidationService;
