/**
 * Tests for NotificationService — registerToken, getPreferences,
 * setPreference.
 *
 * Refs: Design §6.7; AC-F09-4, AC-F09-5
 */

import AuthService from '../../services/AuthService';
import { NotificationService } from '../../services/NotificationService';

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: { getIdToken: jest.fn().mockResolvedValue('mock-token') },
}));

const mockFetch = jest.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).fetch = mockFetch;

const response204 = () => ({ ok: true, status: 204 });
const jsonResponse = (body: unknown, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

const PREFS_STUB = {
  feeding: true,
  sleeping: true,
  bathing: false,
  playing: true,
};

describe('NotificationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('registerToken', () => {
    it('sends timezone from Intl when not overridden', async () => {
      mockFetch.mockResolvedValueOnce(response204());

      await NotificationService.registerToken('fcm-tok');

      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toContain('/friends/fcm-token');
      expect(options.method).toBe('PUT');
      const body = JSON.parse(options.body);
      expect(body.fcm_token).toBe('fcm-tok');
      expect(typeof body.timezone).toBe('string');
      expect(body.timezone.length).toBeGreaterThan(0);
    });

    it('sends explicit timezone when provided', async () => {
      mockFetch.mockResolvedValueOnce(response204());

      await NotificationService.registerToken(
        'fcm-tok',
        'Asia/Ho_Chi_Minh',
      );

      const [, options] = mockFetch.mock.calls[0];
      const body = JSON.parse(options.body);
      expect(body.timezone).toBe('Asia/Ho_Chi_Minh');
    });
  });

  describe('getPreferences', () => {
    it('parses response into NotificationPreferences', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(PREFS_STUB));

      const result = await NotificationService.getPreferences();

      expect(result).toEqual(PREFS_STUB);
      expect(result.bathing).toBe(false);
    });
  });

  describe('setPreference', () => {
    it('calls PUT /notifications/preferences/{type} with enabled body', async () => {
      mockFetch.mockResolvedValueOnce(response204());

      await NotificationService.setPreference('bathing', false);

      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toContain('/notifications/preferences/bathing');
      expect(options.method).toBe('PUT');
      expect(JSON.parse(options.body)).toEqual({ enabled: false });
    });
  });
});
