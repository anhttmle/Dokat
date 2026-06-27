import 'package:firebase_auth/firebase_auth.dart';

/// Sealed class hierarchy for authentication state.
sealed class AuthState {}

/// Firebase is initializing or checking current user.
final class AuthLoading extends AuthState {}

/// User is authenticated and does not need to force-link.
final class AuthAuthenticated extends AuthState {
  AuthAuthenticated({required this.user, required this.isGuest});

  final User user;

  /// True if the user has not linked any OAuth provider yet.
  final bool isGuest;
}

/// User has been a guest for >= 7 days and must link an account.
final class AuthForceLinkRequired extends AuthState {
  AuthForceLinkRequired({required this.user});

  final User user;
}

/// No Firebase user — anonymous sign-in pending.
final class AuthUnauthenticated extends AuthState {}

/// An error occurred during authentication.
final class AuthError extends AuthState {
  AuthError({required this.message});

  final String message;
}
