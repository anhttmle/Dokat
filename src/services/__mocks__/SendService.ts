/**
 * Manual Jest mock for SendService.
 *
 * Activated in tests via ``jest.mock('../../services/SendService')``.
 * ``send`` is a ``jest.fn()`` so tests can stub the result.
 */

const SendService = {
  send: jest.fn(),
};

export default SendService;
