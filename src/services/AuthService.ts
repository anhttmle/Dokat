/**
 * AuthService — wraps Firebase Auth SDK.
 *
 * Responsibilities (Design §4.1):
 *   - signInAnonymously
 *   - getCurrentUser / getIdToken
 *   - linkWithCredential (used by LinkAccountSheet)
 */

import auth from '@react-native-firebase/auth';

type FirebaseCredential = Parameters<
  ReturnType<typeof auth>['currentUser'] extends infer U
    ? U extends { linkWithCredential: (...args: infer A) => unknown }
      ? (...args: A) => unknown
      : never
    : never
>[0];

const AuthService = {
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
};

export default AuthService;
