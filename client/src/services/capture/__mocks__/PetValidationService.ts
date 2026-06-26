/**
 * Manual Jest mock for PetValidationService.
 *
 * Activated via
 * ``jest.mock('../../services/capture/PetValidationService')``.
 * ``validate`` is a ``jest.fn()`` so tests can stub results.
 */

const PetValidationService = {
  validate: jest.fn(),
};

export default PetValidationService;
