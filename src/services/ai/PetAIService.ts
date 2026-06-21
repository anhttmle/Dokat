/**
 * PetAIService — on-device pet recognition (species + gender).
 *
 * Applies gender confidence threshold (≥ 0.70) before exposing the
 * result to callers; a lower-confidence gender prediction is omitted
 * (AC-F02-3, FR-8). The underlying model runner is injected via
 * _petModelStub so it can be mocked in tests independently.
 */

import type { PetGender, PetSpecies } from '../ProfileService';
import { runModel } from './_petModelStub';

const GENDER_CONFIDENCE_THRESHOLD = 0.70;

export interface AIInferenceResult {
  species: PetSpecies;
  confidence: number;
  /** Defined only when gender_confidence >= 0.70 (FR-8). */
  gender?: PetGender;
  gender_confidence?: number;
}

const PetAIService = {
  /**
   * Run on-device inference on an image and return predicted
   * species and (conditionally) gender.
   *
   * @param imageUri - Local URI of the captured/selected image.
   */
  infer: async (imageUri: string): Promise<AIInferenceResult> => {
    const raw = await runModel(imageUri);
    const result: AIInferenceResult = {
      species: raw.species,
      confidence: raw.confidence,
      gender_confidence: raw.gender_confidence,
    };
    if (raw.gender_confidence >= GENDER_CONFIDENCE_THRESHOLD) {
      result.gender = raw.gender;
    }
    return result;
  },
};

export default PetAIService;
