/**
 * _validationModelStub — hardcoded placeholder for on-device human
 * detection inference (F04).
 *
 * Returned until a real on-device AI framework (TFLite / CoreML) is
 * integrated (DL-F04-03). Exported as a named function so tests can
 * mock it independently of PetValidationService.
 */

export interface RawValidationModelResult {
  /** Probability the image contains a human, in [0, 1]. */
  human_confidence: number;
}

/**
 * Run (stub) human-detection inference on a local image URI.
 *
 * @param _imageUri - Local URI; unused by the stub.
 * @returns Hardcoded raw result including human_confidence.
 */
export async function runValidationModel(
  _imageUri: string,
): Promise<RawValidationModelResult> {
  return { human_confidence: 0.1 };
}
