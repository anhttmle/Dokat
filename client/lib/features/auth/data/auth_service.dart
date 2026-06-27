import 'package:firebase_auth/firebase_auth.dart';

/// Handles Firebase authentication operations.
///
/// Covers anonymous sign-in, OAuth link, and sign-out.
/// Does not make HTTP calls — backend auth is handled via
/// Firebase ID Token in [api_client.dart].
class AuthService {
  AuthService({FirebaseAuth? auth})
      : _auth = auth ?? FirebaseAuth.instance;

  final FirebaseAuth _auth;

  /// Stream of Firebase [User] changes.
  Stream<User?> get userChanges => _auth.userChanges();

  /// Current user, or null if not signed in.
  User? get currentUser => _auth.currentUser;

  /// Signs in anonymously, creating a guest account.
  Future<UserCredential> signInAnonymously() =>
      _auth.signInAnonymously();

  /// Links the current anonymous user with Google OAuth.
  Future<UserCredential> linkWithGoogle() async {
    final provider = GoogleAuthProvider();
    provider.addScope('email');
    return _auth.currentUser!.linkWithProvider(provider);
  }

  /// Links the current anonymous user with Apple OAuth.
  Future<UserCredential> linkWithApple() async {
    final provider = AppleAuthProvider();
    return _auth.currentUser!.linkWithProvider(provider);
  }

  /// Links the current anonymous user with Facebook OAuth.
  Future<UserCredential> linkWithFacebook() async {
    final provider = FacebookAuthProvider();
    return _auth.currentUser!.linkWithProvider(provider);
  }

  /// Returns true if the current user has linked at least one
  /// OAuth provider (Google, Apple, or Facebook).
  bool get isLinked {
    final user = _auth.currentUser;
    if (user == null) return false;
    return user.providerData
        .any((info) => info.providerId != 'firebase');
  }

  /// Returns the [DateTime] when the current user was created.
  DateTime? get creationTime =>
      _auth.currentUser?.metadata.creationTime;

  /// Signs out the current user.
  Future<void> signOut() => _auth.signOut();
}
