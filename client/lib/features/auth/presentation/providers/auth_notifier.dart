import 'dart:async' show unawaited;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/auth_service.dart';
import '../../domain/auth_state.dart';

/// Provides [AuthState] and exposes auth operations to the UI.
final authNotifierProvider =
    StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(AuthService(dio: ref.read(dioProvider))),
);

/// Manages authentication state for the entire app.
class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._service) : super(AuthLoading()) {
    unawaited(_init());
  }

  final AuthService _service;

  Future<void> _init() async {
    try {
      if (await _service.hasJwtSession()) {
        final userId = await _service.getJwtUserId();
        if (userId != null) {
          state = AuthAuthenticated(userId: userId);
          return;
        }
      }
      await _service.signInWithDeviceId();
      final userId = await _service.getJwtUserId() ?? '';
      state = AuthAuthenticated(userId: userId);
    } catch (e) {
      state = AuthError(message: e.toString());
    }
  }

  /// Clears JWT and re-establishes a backend session.
  Future<void> signOut() async {
    state = AuthLoading();
    try {
      await _service.signOut();
      final userId = await _service.getJwtUserId() ?? '';
      state = AuthAuthenticated(userId: userId);
    } catch (e) {
      state = AuthError(message: e.toString());
    }
  }
}
