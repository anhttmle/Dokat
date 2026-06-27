import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/auth_service.dart';
import '../../domain/auth_state.dart';

/// Provides [AuthState] and exposes auth operations to the UI.
final authNotifierProvider =
    StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(AuthService()),
);

/// Manages authentication state for the entire app.
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._service) : super(AuthLoading()) {
    _init();
  }

  final AuthService _service;
  StreamSubscription<dynamic>? _sub;

  void _init() {
    _sub = _service.userChanges.listen(_handleUserChange);
  }

  void _handleUserChange(dynamic user) {
    if (user == null) {
      _signInAnonymously();
      return;
    }
    if (_isForceLinkRequired()) {
      state = AuthForceLinkRequired(user: user);
      return;
    }
    state = AuthAuthenticated(
      user: user,
      isGuest: !_service.isLinked,
    );
  }

  bool _isForceLinkRequired() {
    if (_service.isLinked) return false;
    final created = _service.creationTime;
    if (created == null) return false;
    return DateTime.now().difference(created).inDays >= 7;
  }

  Future<void> _signInAnonymously() async {
    try {
      await _service.signInAnonymously();
    } catch (e) {
      state = AuthError(message: e.toString());
    }
  }

  /// Links the current guest with the given [provider].
  ///
  /// [provider] must be one of: 'google', 'apple', 'facebook'.
  Future<void> linkAccount(String provider) async {
    try {
      switch (provider) {
        case 'google':
          await _service.linkWithGoogle();
        case 'apple':
          await _service.linkWithApple();
        case 'facebook':
          await _service.linkWithFacebook();
        default:
          throw ArgumentError('Unknown provider: $provider');
      }
    } catch (e) {
      state = AuthError(message: e.toString());
    }
  }

  /// Signs out and reverts to anonymous.
  Future<void> signOut() async {
    await _service.signOut();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
