import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/profile_service.dart';
import '../../domain/owner_profile.dart';

final profileServiceProvider = Provider<ProfileService>(
  (ref) => ProfileService(dio: ref.read(dioProvider)),
);

/// Provides the current user's [OwnerProfile].
final profileNotifierProvider =
    AsyncNotifierProvider<ProfileNotifier, OwnerProfile?>(
  ProfileNotifier.new,
);

class ProfileNotifier extends AsyncNotifier<OwnerProfile?> {
  @override
  Future<OwnerProfile?> build() async {
    return ref.read(profileServiceProvider).getProfile();
  }

  Future<void> updateProfile(Map<String, dynamic> fields) async {
    final service = ref.read(profileServiceProvider);
    state = await AsyncValue.guard(() => service.updateProfile(fields));
  }
}
