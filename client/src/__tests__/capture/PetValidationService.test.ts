/**
 * Tests for PetValidationService — human-detection block gate.
 *
 * Refs: Design §6.1; FR-4, FR-5; AC-F04-2, AC-F04-3; DL-F04-02
 */

import { runValidationModel } from '../../services/ai/_validationModelStub';
import PetValidationService from '../../services/capture/PetValidationService';

jest.mock('../../services/ai/_validationModelStub');

const mockRun = runValidationModel as jest.Mock;

describe('PetValidationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('allows image when human confidence is low', async () => {
    mockRun.mockResolvedValue({ human_confidence: 0.2 });

    const result = await PetValidationService.validate('file://x.jpg');

    expect(result.allowed).toBe(true);
    expect(result.humanConfidence).toBe(0.2);
  });

  it('blocks image when human confidence is high', async () => {
    mockRun.mockResolvedValue({ human_confidence: 0.95 });

    const result = await PetValidationService.validate('file://x.jpg');

    expect(result.allowed).toBe(false);
  });

  it('blocks at threshold boundary 0.70 (inclusive)', async () => {
    mockRun.mockResolvedValue({ human_confidence: 0.7 });

    const result = await PetValidationService.validate('file://x.jpg');

    expect(result.allowed).toBe(false);
  });

  it('returns the confidence reported by the model', async () => {
    mockRun.mockResolvedValue({ human_confidence: 0.42 });

    const result = await PetValidationService.validate('file://x.jpg');

    expect(result.humanConfidence).toBe(0.42);
  });
});
