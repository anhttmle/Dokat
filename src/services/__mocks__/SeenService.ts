/**
 * Manual Jest mock for SeenService.
 *
 * Activated in tests via ``jest.mock('../../services/SeenService')``.
 * Every method is a ``jest.fn()`` so tests can stub return values.
 */

const SeenService = {
  markSeen: jest.fn(),
  getSeenBy: jest.fn(),
};

export default SeenService;
