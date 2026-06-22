/**
 * Manual Jest mock for FeedService.
 *
 * Activated in tests via ``jest.mock('../../services/FeedService')``.
 * Every method is a ``jest.fn()`` so tests can stub return values.
 */

const FeedService = {
  getFeed: jest.fn(),
  markSeen: jest.fn(),
};

export default FeedService;
