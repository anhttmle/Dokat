/// Sealed class hierarchy for authentication state.
sealed class AuthState {}

/// JWT session is being established.
final class AuthLoading extends AuthState {}

/// User is authenticated via backend JWT.
final class AuthAuthenticated extends AuthState {
  AuthAuthenticated({required this.userId});

  final String userId;
}

/// An error occurred during authentication.
final class AuthError extends AuthState {
  AuthError({required this.message});

  final String message;
}
