import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/auth_state.dart';
import '../providers/auth_notifier.dart';
import 'link_account_sheet.dart';

/// Wraps [child] and shows a link-account prompt when the user
/// is a guest attempting a protected action.
///
/// Shows a loading indicator while auth is initializing.
class AuthGuard extends ConsumerWidget {
  const AuthGuard({
    super.key,
    required this.child,
    this.requireLinked = false,
  });

  final Widget child;

  /// If true, shows [LinkAccountSheet] when user is a guest.
  final bool requireLinked;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);

    return switch (authState) {
      AuthLoading() => const Scaffold(
          body: Center(child: CircularProgressIndicator()),
        ),
      AuthError(:final message) => Scaffold(
          body: Center(child: Text('Auth error: $message')),
        ),
      AuthAuthenticated(:final isGuest) when requireLinked && isGuest =>
        Scaffold(
          body: LinkAccountSheet(
            onDismiss: () =>
                Navigator.of(context).maybePop(),
          ),
        ),
      _ => child,
    };
  }
}
