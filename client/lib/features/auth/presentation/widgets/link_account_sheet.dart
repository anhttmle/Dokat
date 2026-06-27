import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/auth_notifier.dart';

/// Bottom sheet that prompts the user to link an OAuth account.
class LinkAccountSheet extends ConsumerStatefulWidget {
  const LinkAccountSheet({super.key, this.onDismiss});

  /// Called when the user taps the close button (optional).
  final VoidCallback? onDismiss;

  @override
  ConsumerState<LinkAccountSheet> createState() =>
      _LinkAccountSheetState();
}

class _LinkAccountSheetState extends ConsumerState<LinkAccountSheet> {
  bool _loading = false;

  Future<void> _link(String provider) async {
    setState(() => _loading = true);
    await ref.read(authNotifierProvider.notifier).linkAccount(provider);
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Liên kết tài khoản',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                if (widget.onDismiss != null)
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: widget.onDismiss,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Liên kết tài khoản để gửi ảnh và kết bạn.',
            ),
            const SizedBox(height: 24),
            if (_loading)
              const Center(child: CircularProgressIndicator())
            else ...[
              _ProviderButton(
                label: 'Tiếp tục với Google',
                icon: Icons.g_mobiledata,
                onTap: () => _link('google'),
              ),
              const SizedBox(height: 12),
              _ProviderButton(
                label: 'Tiếp tục với Apple',
                icon: Icons.apple,
                onTap: () => _link('apple'),
              ),
              const SizedBox(height: 12),
              _ProviderButton(
                label: 'Tiếp tục với Facebook',
                icon: Icons.facebook,
                onTap: () => _link('facebook'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ProviderButton extends StatelessWidget {
  const _ProviderButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilledButton.tonal(
      onPressed: onTap,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
    );
  }
}
