/**
 * Tests for SocialService — backend API client for F03 social graph.
 *
 * Written TDD-style; tests are expected to FAIL until SocialService
 * is implemented in a later F03 task.
 *
 * Refs: Design §4.2, AC-F03-1, AC-F03-2, AC-F03-9
 */

import AuthService from '../../services/AuthService';
import SocialService from '../../services/SocialService';

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

const GENERATE_QR_STUB = {
  token: '550e8400-e29b-41d4-a716-446655440000',
  deep_link:
    'https://petapp.example.com/add-friend?token=550e8400-e29b-41d4-a716-446655440000',
  expires_at: '2026-06-21T04:05:00Z',
};

const SCAN_RESPONSE_STUB = {
  friendship_id: 'friend-row-uuid',
  friend: {
    user_id: 'abc-uuid',
    display_name: 'Nguyen Van A',
    avatar_url: null,
  },
  created_at: '2026-06-21T04:02:30Z',
};

const FRIENDS_LIST_STUB = {
  friends: [
    {
      user_id: 'abc-uuid',
      display_name: 'Tran Thi B',
      avatar_url: null,
      friendship_created_at: '2026-06-20T10:00:00Z',
    },
  ],
  total: 1,
};

describe('SocialService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('generateQR', () => {
    it('calls POST /friends/qr/generate and returns token data', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(GENERATE_QR_STUB));

      const result = await SocialService.generateQR();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/friends/qr/generate'),
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.token).toBe(GENERATE_QR_STUB.token);
    });
  });

  describe('scanQR', () => {
    it('calls POST /friends/qr/scan with token and returns friendship', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse(SCAN_RESPONSE_STUB, 201),
      );

      const result = await SocialService.scanQR(
        '550e8400-e29b-41d4-a716-446655440000',
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/friends/qr/scan'),
        expect.objectContaining({ method: 'POST' }),
      );
      expect(result.friendship_id).toBe(SCAN_RESPONSE_STUB.friendship_id);
    });
  });

  describe('listFriends', () => {
    it('calls GET /friends and returns friend list', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(FRIENDS_LIST_STUB));

      const result = await SocialService.listFriends();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/friends'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result.friends).toHaveLength(1);
    });
  });

  describe('removeFriend', () => {
    it('calls DELETE /friends/{id} and resolves on 204', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(
        SocialService.removeFriend('abc-uuid'),
      ).resolves.toBeUndefined();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/friends/abc-uuid'),
        expect.objectContaining({ method: 'DELETE' }),
      );
    });
  });

  describe('updateFCMToken', () => {
    it('calls PUT /friends/fcm-token with token and resolves on 204', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(
        SocialService.updateFCMToken('fcm-token-abc'),
      ).resolves.toBeUndefined();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/friends/fcm-token'),
        expect.objectContaining({ method: 'PUT' }),
      );
    });
  });

  describe('getFriends', () => {
    it('calls GET /friends and returns friend list', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(FRIENDS_LIST_STUB));

      const result = await SocialService.getFriends();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/friends'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result.friends).toHaveLength(1);
    });
  });
});
