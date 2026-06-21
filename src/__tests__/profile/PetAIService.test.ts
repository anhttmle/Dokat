/**
 * Tests for PetAIService — on-device inference (Design §4.1).
 *
 * Written TDD-style; tests are expected to FAIL until PetAIService is
 * implemented in later F02 tasks.
 */

import PetAIService from '../../services/ai/PetAIService';

describe('PetAIService', () => {
  describe('infer', () => {
    it('returns species, gender, and a confidence score', async () => {
      const result = await PetAIService.infer('file:///tmp/dog.jpg');

      expect(['dog', 'cat']).toContain(result.species);
      expect(['male', 'female', 'unknown']).toContain(result.gender);
      expect(result.confidence).toBeGreaterThanOrEqual(0);
      expect(result.confidence).toBeLessThanOrEqual(1);
    });
  });
});
