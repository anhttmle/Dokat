/**
 * Manual Jest mock for SettingsService.
 *
 * Activated in tests via ``jest.mock('../../services/SettingsService')``.
 * Every method is a ``jest.fn()`` so tests can stub return values.
 */

const SettingsService = {
  unlinkProvider: jest.fn(),
  blockUser: jest.fn(),
  unblockUser: jest.fn(),
  listBlocked: jest.fn(),
  reportUser: jest.fn(),
  logout: jest.fn(),
};

export default SettingsService;
