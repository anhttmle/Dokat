import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/notification_service.dart';

final _notifPrefsProvider =
    FutureProvider<Map<String, bool>>((ref) async {
  return NotificationService(dio: ref.read(dioProvider))
      .getPreferences();
});

/// Settings section for toggling notification preferences.
class NotificationPreferenceSection extends ConsumerWidget {
  const NotificationPreferenceSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefsAsync = ref.watch(_notifPrefsProvider);

    return prefsAsync.when(
      loading: () => const CircularProgressIndicator(),
      error: (e, _) => Text('Lỗi tải preferences: $e'),
      data: (prefs) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Thông báo',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          ...prefs.entries.map(
            (entry) => SwitchListTile(
              title: Text(_label(entry.key)),
              value: entry.value,
              onChanged: (enabled) async {
                await NotificationService(dio: ref.read(dioProvider))
                    .updatePreference(entry.key, enabled: enabled);
                ref.invalidate(_notifPrefsProvider);
              },
            ),
          ),
        ],
      ),
    );
  }

  String _label(String type) {
    return switch (type) {
      'new_photo' => 'Ảnh mới từ bạn bè',
      'friend_request' => 'Kết bạn mới',
      _ => type,
    };
  }
}
