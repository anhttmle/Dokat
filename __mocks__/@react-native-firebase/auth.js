/**
 * Manual mock for @react-native-firebase/auth
 * Covers: signInAnonymously, currentUser, getIdToken, linkWithCredential
 */

const mockUser = {
  uid: 'test-anonymous-uid',
  isAnonymous: true,
  getIdToken: jest.fn().mockResolvedValue('mock-firebase-id-token'),
  linkWithCredential: jest.fn().mockResolvedValue({
    user: {
      uid: 'test-anonymous-uid',
      isAnonymous: false,
      getIdToken: jest.fn().mockResolvedValue('mock-linked-token'),
    },
  }),
};

const mockAuthInstance = {
  signInAnonymously: jest.fn().mockResolvedValue({ user: mockUser }),
  currentUser: mockUser,
  onAuthStateChanged: jest.fn().mockReturnValue(jest.fn()),
};

const auth = jest.fn(() => mockAuthInstance);

auth.GoogleAuthProvider = {
  credential: jest.fn().mockReturnValue({ providerId: 'google.com' }),
};

auth.OAuthProvider = jest.fn((providerId) => ({
  credential: jest.fn().mockReturnValue({ providerId }),
}));

module.exports = auth;
module.exports.default = auth;
