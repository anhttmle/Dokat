/**
 * Manual Jest mock for PetAIService.
 *
 * Activated in tests via ``jest.mock('../../services/ai/PetAIService')``.
 * ``infer`` is a ``jest.fn()`` so tests can stub inference results.
 */

const PetAIService = {
  infer: jest.fn(),
};

export default PetAIService;
