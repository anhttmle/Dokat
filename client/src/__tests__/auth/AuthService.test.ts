/**
 * Tests for AuthService — wraps Firebase Auth SDK.
 * Firebase is mocked via jest.config.js moduleNameMapper.
 *
 * Design ref: §4.1
 */

import AuthService from '../../services/AuthService';
import AsyncStorage from '@react-native-async-storage/async-storage';

const mockAuth = require('@react-native-firebase/auth');

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset currentUser to default mock user before each test.
    mockAuth().currentUser = {
      uid: 'test-anonymous-uid',
      isAnonymous: true,
      getIdToken: jest.fn().mockResolvedValue('mock-firebase-id-token'),
      linkWithCredential: jest.fn(),
    };
  });

  describe('signInAnonymously', () => {
    it('delegates to firebase auth().signInAnonymously()', async () => {
      const mockCredential = { user: { uid: 'anon-123', isAnonymous: true } };
      mockAuth().signInAnonymously.mockResolvedValueOnce(mockCredential);

      const result = await AuthService.signInAnonymously();

      expect(mockAuth().signInAnonymously).toHaveBeenCalledTimes(1);
      expect(result).toEqual(mockCredential);
    });
  });

  describe('getCurrentUser', () => {
    it('returns current user from firebase auth instance', () => {
      const mockUser = { uid: 'uid-123', isAnonymous: true };
      mockAuth().currentUser = mockUser;

      const result = AuthService.getCurrentUser();

      expect(result).toEqual(mockUser);
    });

    it('returns null when no user is signed in', () => {
      mockAuth().currentUser = null;

      const result = AuthService.getCurrentUser();

      expect(result).toBeNull();
    });
  });

  describe('getIdToken', () => {
    it('returns ID token string from current user', async () => {
      const token = 'firebase-id-token-abc';
      mockAuth().currentUser.getIdToken.mockResolvedValueOnce(token);

      const result = await AuthService.getIdToken();

      expect(result).toBe(token);
    });

    it('returns null when there is no current user', async () => {
      mockAuth().currentUser = null;

      const result = await AuthService.getIdToken();

      expect(result).toBeNull();
    });
  });

  describe('linkWithCredential', () => {
    it('calls linkWithCredential on current user and returns credential', async () => {
      const mockCredential = { providerId: 'google.com' };
      const mockLinkedUser = { uid: 'uid-123', isAnonymous: false };
      mockAuth().currentUser.linkWithCredential.mockResolvedValueOnce({
        user: mockLinkedUser,
      });

      const result = await AuthService.linkWithCredential(mockCredential);

      expect(mockAuth().currentUser.linkWithCredential).toHaveBeenCalledWith(
        mockCredential,
      );
      expect(result.user).toEqual(mockLinkedUser);
    });

    it('throws when there is no current user to link', async () => {
      mockAuth().currentUser = null;

      await expect(AuthService.linkWithCredential({})).rejects.toThrow(
        'No authenticated user to link',
      );
    });
  });
});

describe('AuthService.init', () => {
  const FIREBASE_UID_KEY = 'auth:firebase_uid';

  beforeEach(async () => {
    jest.clearAllMocks();
    await AsyncStorage.clear();
    mockAuth().currentUser = null;
  });

  it('signs in anonymously and saves uid to storage when no session exists', async () => {
    // test_sign_in_anonymous_saves_uid_to_storage
    // Storage is empty, no current user → must call signInAnonymously
    const newUid = 'anon-new-uid';
    mockAuth().signInAnonymously.mockResolvedValueOnce({
      user: { uid: newUid, isAnonymous: true },
    });

    await AuthService.init();

    expect(mockAuth().signInAnonymously).toHaveBeenCalledTimes(1);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      FIREBASE_UID_KEY,
      newUid,
    );
  });

  it('restores session without calling signInAnonymously when uid is in storage', async () => {
    // test_restore_session_reads_from_storage
    // Storage has a uid and Firebase still has a current user
    await AsyncStorage.setItem(FIREBASE_UID_KEY, 'existing-uid');
    mockAuth().currentUser = {
      uid: 'existing-uid',
      isAnonymous: true,
      getIdToken: jest.fn().mockResolvedValue('token'),
    };

    await AuthService.init();

    expect(mockAuth().signInAnonymously).not.toHaveBeenCalled();
  });

  it('getIdToken returns current token from firebase user', async () => {
    // test_get_id_token_returns_current_token
    const expectedToken = 'firebase-token-from-current-user';
    mockAuth().currentUser = {
      uid: 'uid-abc',
      isAnonymous: true,
      getIdToken: jest.fn().mockResolvedValueOnce(expectedToken),
    };

    const result = await AuthService.getIdToken();

    expect(result).toBe(expectedToken);
  });
});
