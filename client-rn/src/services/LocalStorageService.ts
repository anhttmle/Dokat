/**
 * LocalStorageService — persists auth-related data via AsyncStorage.
 *
 * Responsibilities (Design §4.1, FR-2, FR-3, FR-6):
 *   - firebase_uid: survive app background/foreground cycles
 *   - force_link_at: client-side deadline check without a network call
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  FIREBASE_UID: 'auth:firebase_uid',
  FORCE_LINK_AT: 'auth:force_link_at',
} as const;

const LocalStorageService = {
  saveFirebaseUid: (uid: string): Promise<void> =>
    AsyncStorage.setItem(KEYS.FIREBASE_UID, uid),

  getFirebaseUid: (): Promise<string | null> =>
    AsyncStorage.getItem(KEYS.FIREBASE_UID),

  saveForceLinkAt: (date: Date): Promise<void> =>
    AsyncStorage.setItem(KEYS.FORCE_LINK_AT, date.toISOString()),

  getForceLinkAt: async (): Promise<Date | null> => {
    const value = await AsyncStorage.getItem(KEYS.FORCE_LINK_AT);
    return value ? new Date(value) : null;
  },

  clear: (): Promise<readonly Error[]> =>
    AsyncStorage.multiRemove([KEYS.FIREBASE_UID, KEYS.FORCE_LINK_AT]),
};

export default LocalStorageService;
