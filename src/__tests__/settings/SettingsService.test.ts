/**
 * Tests for SettingsService — backend API client for F10 settings.
 *
 * Mocks fetch and AuthService.getIdToken (same pattern as
 * SocialService.test.ts). Link is NOT covered here — it reuses
 * POST /auth/link from F01 (DL-F10-01).
 *
 * Refs: Design §3, §4.2, §6.7; FR-3, FR-6, FR-8, FR-9;
 *       AC-F10-5; DL-F10-01, DL-F10-09
 */

import AuthService from '../../services/AuthService';
import SettingsService from '../../services/SettingsService';

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: { getIdToken: jest.fn().mockResolvedValue('mock-token') },
}));

const mockFetch = jest.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).fetch = mockFetch;

const jsonResponse = (body: unknown, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

const BLOCK_LIST_STUB = {
  blocked: [
    {
      user_id: 'b-uuid',
      display_name: 'Beta',
      avatar_url: null,
      blocked_at: '2026-06-22T07:00:00Z',
    },
  ],
  total: 1,
};

describe('SettingsService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  it('blockUser posts to /users/block with user_id body', async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ blocked_user_id: 'b-uuid' }, 201),
    );

    await SettingsService.blockUser('b-uuid');

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/users/block');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({ user_id: 'b-uuid' });
  });

  it('unblockUser deletes /users/block/{id}', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    await SettingsService.unblockUser('b-uuid');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/users/block/b-uuid'),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('listBlocked parses { blocked, total }', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(BLOCK_LIST_STUB));

    const result = await SettingsService.listBlocked();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/users/block'),
      expect.objectContaining({ method: 'GET' }),
    );
    expect(result.blocked).toHaveLength(1);
    expect(result.total).toBe(1);
  });

  it('reportUser posts to /users/report with reason', async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ report_id: 'r-uuid' }, 201),
    );

    await SettingsService.reportUser('b-uuid', 'spam');

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/users/report');
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({
      user_id: 'b-uuid',
      reason: 'spam',
    });
  });

  it('unlinkProvider deletes /users/providers/{p}', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    await SettingsService.unlinkProvider('google');

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/users/providers/google'),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('logout posts to /users/logout', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    await SettingsService.logout();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/users/logout'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('attaches the Authorization bearer header to every request', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(BLOCK_LIST_STUB));

    await SettingsService.listBlocked();

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer mock-token');
  });
});
