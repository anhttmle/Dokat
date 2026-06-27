import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

/// Handles Firebase authentication operations.
///
/// Covers anonymous sign-in, OAuth link, and sign-out.
/// Calls [syncSession] after every successful sign-in to upsert the
/// user row in the backend database via POST /auth/session.
class AuthService {
  AuthService({FirebaseAuth? auth, Dio? dio})
      : _auth = auth ?? FirebaseAuth.instance,
        _dio = dio;

  final FirebaseAuth _auth;
  final Dio? _dio;

  /// Stream of Firebase [User] changes.
  Stream<User?> get userChanges => _auth.userChanges();

  /// Current user, or null if not signed in.
  User? get currentUser => _auth.currentUser;

  /// Upserts the user row in the backend database.
  ///
  /// Must be called after any successful Firebase sign-in so that
  /// all subsequent API calls find the user in the DB.
  Future<void> syncSession() async {
    if (_dio == null) return;
    try {
      await _dio.post<dynamic>('/auth/session');
    } catch (_) {
      // Sync failures are non-fatal; the next API call will surface
      // a meaningful error if the session is still missing.
    }
  }

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
