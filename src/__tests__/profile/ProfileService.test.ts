/**
 * Tests for ProfileService — backend API client (Design §4.1).
 *
 * Written TDD-style; tests are expected to FAIL until ProfileService
 * is implemented in later F02 tasks. The HTTP transport is assumed to
 * be the global ``fetch`` (DL-F02-08).
 */

import AuthService from '../../services/AuthService';
import ProfileService from '../../services/ProfileService';

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

const OWNER_PROFILE_STUB = {
  user_id: 'user-1',
  display_name: 'Nguyen Van A',
  avatar_url: null,
  is_anonymous: false,
  providers: ['google'],
};

describe('ProfileService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('getOwnerProfile', () => {
    it('calls GET /profile/me with Authorization header', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(OWNER_PROFILE_STUB));

      await ProfileService.getOwnerProfile();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toMatch(/\/profile\/me$/);
      expect(options?.method ?? 'GET').toBe('GET');
      expect(options?.headers?.Authorization).toBe('Bearer mock-token');
    });

    it('returns the parsed owner profile', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse(OWNER_PROFILE_STUB));

      const result = await ProfileService.getOwnerProfile();

      expect(result.userId).toBe('user-1');
      expect(result.displayName).toBe('Nguyen Van A');
      expect(result.isAnonymous).toBe(false);
    });
  });

  describe('patchOwnerProfile', () => {
    it('calls PATCH /profile/me and body only contains passed fields', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({
          ...OWNER_PROFILE_STUB,
          display_name: 'New Name',
        }),
      );

      await ProfileService.patchOwnerProfile({ displayName: 'New Name' });

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toMatch(/\/profile\/me$/);
      expect(options?.method).toBe('PATCH');
      const body = JSON.parse(options?.body ?? '{}');
      expect(body).toEqual({ display_name: 'New Name' });
      expect(body).not.toHaveProperty('avatar_url');
    });

    it('sends a partial update and returns the new profile', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({
          ...OWNER_PROFILE_STUB,
          display_name: 'New Name',
        }),
      );

      const result = await ProfileService.patchOwnerProfile({
        displayName: 'New Name',
      });

      expect(result.displayName).toBe('New Name');
    });
  });

  describe('createPet', () => {
    it('creates a pet and returns the created entity', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse(
          {
            id: 'pet-1',
            name: 'Mochi',
            species: 'dog',
            gender: 'male',
            birthdate: '2022-03-15',
            avatar_url: null,
            created_at: '2026-06-21T09:00:00Z',
          },
          201,
        ),
      );

      const result = await ProfileService.createPet({
        name: 'Mochi',
        species: 'dog',
        gender: 'male',
      });

      expect(result.id).toBe('pet-1');
      expect(result.species).toBe('dog');
    });
  });
});
