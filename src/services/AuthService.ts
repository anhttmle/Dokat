/**
 * AuthService — wraps Firebase Auth SDK.
 *
 * Responsibilities (Design §4.1):
 *   - init: restore session from storage or sign in anonymously
 *   - signInAnonymously
 *   - getCurrentUser / getIdToken
 *   - linkWithCredential (used by LinkAccountSheet)
 */

import auth from '@react-native-firebase/auth';

import LocalStorageService from './LocalStorageService';

type FirebaseCredential = Parameters<
  ReturnType<typeof auth>['currentUser'] extends infer U
    ? U extends { linkWithCredential: (...args: infer A) => unknown }
      ? (...args: A) => unknown
      : never
    : never
>[0];

const AuthService = {
  /**
   * Initialise the auth session on app start.
   *
   * If a firebase_uid is already saved in storage **and** Firebase still
   * holds a valid credential (currentUser is non-null), the existing
   * session is restored silently.  Otherwise a new anonymous sign-in is
   * performed and the resulting uid is persisted.
   *
   * Design §4.1 (FR-1, FR-2, FR-3).
   */
  init: async (): Promise<void> => {
    const storedUid = await LocalStorageService.getFirebaseUid();
    const currentUser = auth().currentUser;

    if (storedUid && currentUser) {
      return;
    }

    const credential = await auth().signInAnonymously();
    await LocalStorageService.saveFirebaseUid(credential.user.uid);
  },

  signInAnonymously: () => auth().signInAnonymously(),

  getCurrentUser: () => auth().currentUser,

  getIdToken: async (): Promise<string | null> => {
    const user = auth().currentUser;
    if (!user) {
      return null;
    }
    return user.getIdToken();
  },

  linkWithCredential: async (credential: FirebaseCredential) => {
    const user = auth().currentUser;
    if (!user) {
      throw new Error('No authenticated user to link');
    }
    return user.linkWithCredential(credential);
  },

  /**
   * Link the current user to an OAuth provider by name.
   *
   * Maps the provider name ("google", "apple", "facebook") to the
   * corresponding Firebase OAuthProvider and calls ``linkWithCredential``.
   * The actual native OAuth sign-in flow must be initiated before calling
   * this; this method finalises the Firebase credential linkage.
   *
   * Design §4.1 (FR-7, FR-11).
   *
   * @param provider - Short provider name: "google" | "apple" | "facebook".
   */
  linkWithProvider: async (provider: string): Promise<void> => {
    const user = auth().currentUser;
    if (!user) {
      throw new Error('No authenticated user to link');
    }
    const providerId = `${provider}.com`;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const oauthProvider = new (auth as any).OAuthProvider(providerId);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await user.linkWithCredential(oauthProvider.credential() as any);
  },
};

export default AuthService;
