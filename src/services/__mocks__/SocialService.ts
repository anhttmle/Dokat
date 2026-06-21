/**
 * Manual Jest mock for SocialService.
 *
 * Activated in tests via ``jest.mock('../../services/SocialService')``.
 * Every method is a ``jest.fn()`` so tests can stub return values.
 */

const SocialService = {
  generateQR: jest.fn(),
  scanQR: jest.fn(),
  listFriends: jest.fn(),
  getFriends: jest.fn(),
  removeFriend: jest.fn(),
  updateFCMToken: jest.fn(),
};

export default SocialService;
