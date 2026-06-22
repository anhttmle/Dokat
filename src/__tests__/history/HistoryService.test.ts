/**
 * Tests for HistoryService — backend API client for the F08 history.
 *
 * Mocks fetch and AuthService.getIdToken (same pattern as
 * FeedService.test.ts).
 *
 * Refs: Design §4.2, §6.5; FR-1, FR-2; AC-F08-2; DL-F08-04
 */

import AuthService from '../../services/AuthService';
import HistoryService from '../../services/HistoryService';

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

const SENT_STUB = {
  items: [
    {
      post_id: 'p1',
      cdn_url: 'https://cdn/p1.jpg',
      created_at: '2026-06-22T07:00:00Z',
      recipient_count: 3,
      seen_count: 2,
    },
  ],
  next_cursor: null,
};

const RECEIVED_STUB = {
  items: [
    {
      post_id: 'p2',
      sender_id: 's2',
      sender_display_name: 'Anh',
      sender_avatar_url: null,
      pet_name: 'Mướp',
      cdn_url: 'https://cdn/p2.jpg',
      created_at: '2026-06-22T07:00:00Z',
      seen: true,
    },
  ],
  next_cursor: null,
};

describe('HistoryService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('getSent', () => {
    it('calls GET /history/sent and parses items/next_cursor', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(SENT_STUB));

      const result = await HistoryService.getSent();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/history/sent'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result.items).toHaveLength(1);
      expect(result.items[0].recipient_count).toBe(3);
      expect(result.next_cursor).toBeNull();
    });
  });

  describe('getReceived', () => {
    it('calls GET /history/received and parses the result', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(RECEIVED_STUB));

      const result = await HistoryService.getReceived();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/history/received'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result.items).toHaveLength(1);
      expect(result.items[0].pet_name).toBe('Mướp');
    });
  });

  it('passes the cursor as a query string', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(SENT_STUB));

    await HistoryService.getSent('cursor-abc');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('cursor=cursor-abc');
  });

  it('attaches the Authorization bearer header', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(RECEIVED_STUB));

    await HistoryService.getReceived();

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer mock-token');
  });
});
