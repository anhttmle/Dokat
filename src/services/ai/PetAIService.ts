/**
 * PetAIService — on-device pet recognition (species + gender).
 *
 * Skeleton for F02 task 1.2. The concrete inference framework
 * (TFLite / CoreML / ONNX) is undecided (DL-F02-02); this module
 * exposes the stable interface the UI depends on.
 */

import type { PetGender, PetSpecies } from '../ProfileService';

export interface AIInferenceResult {
  species: PetSpecies;
  gender: PetGender;
  confidence: number;
}

const NOT_IMPLEMENTED = 'PetAIService not implemented yet';

const PetAIService = {
  /**
   * Run on-device inference on an image and return predicted
   * species, gender, and a confidence score in [0, 1].
   *
   * @param _imageUri - Local URI of the captured/selected image.
   */
  infer: async (_imageUri: string): Promise<AIInferenceResult> => {
    throw new Error(NOT_IMPLEMENTED);
  },
};

export default PetAIService;
