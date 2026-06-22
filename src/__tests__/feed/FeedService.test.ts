/**
 * Tests for FeedService — backend API client for the F06 feed.
 *
 * Mocks fetch and AuthService.getIdToken (same pattern as
 * SocialService.test.ts).
 *
 * Refs: Design §4.2; FR-1, FR-5; AC-F06-1; DL-F06-02, DL-F06-08
 */

import AuthService from '../../services/AuthService';
import FeedService from '../../services/FeedService';

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

const FEED_STUB = {
  items: [
    {
      post_id: 'p1',
      sender_id: 's1',
      sender_display_name: 'Anh',
      sender_avatar_url: null,
      pet_name: 'Mướp',
      cdn_url: 'https://cdn/p1.jpg',
      created_at: '2026-06-22T07:00:00Z',
      seen: false,
    },
  ],
  next_cursor: null,
};

describe('FeedService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('getFeed', () => {
    it('calls GET /feed and parses items/next_cursor', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(FEED_STUB));

      const result = await FeedService.getFeed();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/feed'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result.items).toHaveLength(1);
      expect(result.next_cursor).toBeNull();
    });

    it('passes the cursor as a query string', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(FEED_STUB));

      await FeedService.getFeed('cursor-abc');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('cursor=cursor-abc');
    });

    it('attaches the Authorization bearer header', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(FEED_STUB));

      await FeedService.getFeed();

      const [, options] = mockFetch.mock.calls[0];
      expect(options.headers.Authorization).toBe('Bearer mock-token');
    });
  });

  describe('markSeen', () => {
    it('resolves without issuing a network call (F07 hook)', async () => {
      await expect(FeedService.markSeen('p1')).resolves.toBeUndefined();
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
