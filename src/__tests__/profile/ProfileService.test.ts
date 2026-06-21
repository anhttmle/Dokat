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

describe('ProfileService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AuthService.getIdToken as jest.Mock).mockResolvedValue('mock-token');
  });

  describe('getOwnerProfile', () => {
    it('returns the parsed owner profile', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({
          user_id: 'user-1',
          display_name: 'Nguyen Van A',
          avatar_url: null,
          is_anonymous: false,
          providers: ['google'],
        }),
      );

      const result = await ProfileService.getOwnerProfile();

      expect(result.userId).toBe('user-1');
      expect(result.displayName).toBe('Nguyen Van A');
      expect(result.isAnonymous).toBe(false);
    });
  });

  describe('patchOwnerProfile', () => {
    it('sends a partial update and returns the new profile', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({
          user_id: 'user-1',
          display_name: 'New Name',
          avatar_url: null,
          is_anonymous: false,
          providers: [],
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
