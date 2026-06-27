import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/providers.dart';
import '../../../auth/domain/auth_state.dart';
import '../../../auth/presentation/providers/auth_notifier.dart';
import '../../../notifications/presentation/widgets/notification_preference_section.dart';
import '../../data/settings_service.dart';
import '../widgets/account_link_row.dart';

/// App settings screen — account links, notifications, logout.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authNotifierProvider);
    final isGuest = authState is AuthAuthenticated && authState.isGuest;

    return Scaffold(
      appBar: AppBar(title: const Text('Cài đặt')),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.person_outline),
            title: const Text('Hồ sơ'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.push('/settings/profile'),
          ),
          const Divider(),
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 8,
            ),
            child: Text(
              'Tài khoản liên kết',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          AccountLinkRow(
            provider: 'google',
            label: 'Google',
            icon: Icons.g_mobiledata,
            isLinked: !isGuest,
            onUnlink: () => _unlink(context, ref, 'google'),
          ),
          AccountLinkRow(
            provider: 'apple',
            label: 'Apple',
            icon: Icons.apple,
            isLinked: false,
            onUnlink: () => _unlink(context, ref, 'apple'),
          ),
          AccountLinkRow(
            provider: 'facebook',
            label: 'Facebook',
            icon: Icons.facebook,
            isLinked: false,
            onUnlink: () => _unlink(context, ref, 'facebook'),
          ),
          const Divider(),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: NotificationPreferenceSection(),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text(
              'Đăng xuất',
              style: TextStyle(color: Colors.red),
            ),
            onTap: () => _logout(context, ref),
          ),
        ],
      ),
    );
  }

  Future<void> _unlink(
    BuildContext context,
    WidgetRef ref,
    String provider,
  ) async {
    await SettingsService(dio: ref.read(dioProvider))
        .unlinkProvider(provider);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã hủy liên kết.')),
      );
    }
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    await SettingsService(dio: ref.read(dioProvider)).logout();
    await ref.read(authNotifierProvider.notifier).signOut();
  }
}
