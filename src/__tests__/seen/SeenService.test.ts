/**
 * Tests for SeenService — backend API client for F07 seen state.
 *
 * Mocks fetch and AuthService.getIdToken (same pattern as
 * FeedService.test.ts).
 *
 * Refs: Design §4.2, §6.3; FR-1, FR-3, FR-4;
 *   AC-F07-1, AC-F07-2; DL-F07-05
 */

import AuthService from '../../services/AuthService';
import SeenService from '../../services/SeenService';

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

const SEEN_BY_STUB = {
  post_id: 'p1',
  seen_count: 2,
  viewers: [
    {
      user_id: 'u1',
      display_name: 'Châu',
      avatar_url: null,
      seen_at: '2026-06-22T07:05:00Z',
    },
    {
      user_id: 'u2',
      display_name: 'Bình',
      avatar_url: null,
      seen_at: '2026-06-22T07:02:00Z',
    },
  ],
};

describe('SeenService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('markSeen', () => {
    it('POSTs to /posts/{id}/seen', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ post_id: 'p1' }));

      await SeenService.markSeen('p1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/posts/p1/seen'),
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('attaches the Authorization bearer header', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ post_id: 'p1' }));

      await SeenService.markSeen('p1');

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers.Authorization).toBe('Bearer mock-token');
    });
  });

  describe('getSeenBy', () => {
    it('GETs /seen-by and parses the result', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(SEEN_BY_STUB));

      const result = await SeenService.getSeenBy('p1');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/posts/p1/seen-by'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result.post_id).toBe('p1');
      expect(result.seen_count).toBe(2);
      expect(result.viewers).toHaveLength(2);
    });

    it('attaches the Authorization bearer header', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(SEEN_BY_STUB));

      await SeenService.getSeenBy('p1');

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers.Authorization).toBe('Bearer mock-token');
    });
  });
});
