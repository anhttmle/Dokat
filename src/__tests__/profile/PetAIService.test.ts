/**
 * Tests for PetAIService — on-device inference (Design §4.1).
 *
 * The internal model runner (_petModelStub) is mocked so tests can
 * control raw model output independently of the stub implementation.
 */

import PetAIService from '../../services/ai/PetAIService';
import { runModel } from '../../services/ai/_petModelStub';

jest.mock('../../services/ai/_petModelStub');

const mockRunModel = runModel as jest.MockedFunction<typeof runModel>;

describe('PetAIService', () => {
  describe('infer', () => {
    it(
      'returns species, confidence, gender, and gender_confidence ' +
        'when gender_confidence >= 0.70',
      async () => {
        mockRunModel.mockResolvedValueOnce({
          species: 'dog',
          confidence: 0.92,
          gender: 'male',
          gender_confidence: 0.85,
        });

        const result = await PetAIService.infer('file:///tmp/dog.jpg');

        expect(result.species).toBe('dog');
        expect(result.confidence).toBe(0.92);
        expect(result.gender).toBe('male');
        expect(result.gender_confidence).toBe(0.85);
      },
    );

    it(
      'sets gender to undefined when gender_confidence < 0.70',
      async () => {
        mockRunModel.mockResolvedValueOnce({
          species: 'cat',
          confidence: 0.88,
          gender: 'female',
          gender_confidence: 0.60,
        });

        const result = await PetAIService.infer('file:///tmp/cat.jpg');

        expect(result.species).toBe('cat');
        expect(result.gender).toBeUndefined();
        expect(result.gender_confidence).toBe(0.60);
      },
    );
  });
});
