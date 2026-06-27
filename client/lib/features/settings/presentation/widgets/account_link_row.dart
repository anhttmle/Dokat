import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/providers/auth_notifier.dart';

/// A settings row showing an OAuth provider's linked status
/// with the option to link or unlink it.
class AccountLinkRow extends ConsumerWidget {
  const AccountLinkRow({
    super.key,
    required this.provider,
    required this.label,
    required this.icon,
    required this.isLinked,
    required this.onUnlink,
  });

  final String provider;
  final String label;
  final IconData icon;
  final bool isLinked;
  final VoidCallback onUnlink;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: Icon(icon),
      title: Text(label),
      trailing: isLinked
          ? OutlinedButton(
              onPressed: onUnlink,
              child: const Text('Hủy liên kết'),
            )
          : FilledButton.tonal(
              onPressed: () =>
                  ref.read(authNotifierProvider.notifier).linkAccount(provider),
              child: const Text('Liên kết'),
            ),
    );
  }
}
