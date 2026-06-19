/**
 * Tests for LocalStorageService — persists auth data via AsyncStorage.
 * AsyncStorage is mocked via jest.config.js moduleNameMapper.
 *
 * Design ref: §4.1 (FR-2, FR-3, FR-6)
 */

import LocalStorageService from '../../services/LocalStorageService';
import AsyncStorage from '@react-native-async-storage/async-storage';

const FIREBASE_UID_KEY = 'auth:firebase_uid';
const FORCE_LINK_AT_KEY = 'auth:force_link_at';

describe('LocalStorageService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('saveFirebaseUid', () => {
    it('stores firebase uid with the correct AsyncStorage key', async () => {
      await LocalStorageService.saveFirebaseUid('uid-xyz');

      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        FIREBASE_UID_KEY,
        'uid-xyz',
      );
    });
  });

  describe('getFirebaseUid', () => {
    it('reads firebase uid using the correct AsyncStorage key', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce('uid-xyz');

      const result = await LocalStorageService.getFirebaseUid();

      expect(AsyncStorage.getItem).toHaveBeenCalledWith(FIREBASE_UID_KEY);
      expect(result).toBe('uid-xyz');
    });

    it('returns null when no uid is stored', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce(null);

      const result = await LocalStorageService.getFirebaseUid();

      expect(result).toBeNull();
    });
  });

  describe('saveForceLinkAt', () => {
    it('persists force_link_at date as ISO string', async () => {
      const date = new Date('2026-06-25T00:00:00.000Z');

      await LocalStorageService.saveForceLinkAt(date);

      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        FORCE_LINK_AT_KEY,
        '2026-06-25T00:00:00.000Z',
      );
    });
  });

  describe('getForceLinkAt', () => {
    it('returns a Date parsed from the stored ISO string', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce(
        '2026-06-25T00:00:00.000Z',
      );

      const result = await LocalStorageService.getForceLinkAt();

      expect(result).toEqual(new Date('2026-06-25T00:00:00.000Z'));
    });

    it('returns null when no force_link_at is stored', async () => {
      (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce(null);

      const result = await LocalStorageService.getForceLinkAt();

      expect(result).toBeNull();
    });
  });

  describe('clear', () => {
    it('removes all auth keys from AsyncStorage', async () => {
      await LocalStorageService.clear();

      expect(AsyncStorage.multiRemove).toHaveBeenCalledWith([
        FIREBASE_UID_KEY,
        FORCE_LINK_AT_KEY,
      ]);
    });
  });
});
