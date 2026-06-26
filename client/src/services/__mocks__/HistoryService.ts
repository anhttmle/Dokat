/**
 * Manual Jest mock for HistoryService.
 *
 * Activated in tests via ``jest.mock('../../services/HistoryService')``.
 * Every method is a ``jest.fn()`` so tests can stub return values.
 */

const HistoryService = {
  getSent: jest.fn(),
  getReceived: jest.fn(),
};

export default HistoryService;
