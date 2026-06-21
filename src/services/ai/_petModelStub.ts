/**
 * _petModelStub — hardcoded placeholder for on-device model inference.
 *
 * Returned until a real AI framework (TFLite / CoreML / ONNX) is
 * selected (DL-F02-02). Exported as a named function so tests can
 * mock it independently of PetAIService.
 */

import type { PetGender, PetSpecies } from '../ProfileService';

export interface RawModelResult {
  species: PetSpecies;
  confidence: number;
  gender: PetGender;
  gender_confidence: number;
}

/**
 * Run (stub) model inference on a local image URI.
 *
 * @param _imageUri - Local URI; unused by the stub.
 * @returns Hardcoded raw result including gender_confidence.
 */
export async function runModel(
  _imageUri: string,
): Promise<RawModelResult> {
  return {
    species: 'dog',
    confidence: 0.92,
    gender: 'male',
    gender_confidence: 0.85,
  };
}
