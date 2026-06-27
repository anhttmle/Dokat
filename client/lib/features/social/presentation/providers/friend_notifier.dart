import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/social_service.dart';
import '../../domain/friend.dart';

final socialServiceProvider = Provider<SocialService>(
  (ref) => SocialService(dio: ref.read(dioProvider)),
);

/// Provides the current user's friend list.
final friendNotifierProvider =
    AsyncNotifierProvider<FriendNotifier, List<Friend>>(
  FriendNotifier.new,
);

class FriendNotifier extends AsyncNotifier<List<Friend>> {
  @override
  Future<List<Friend>> build() async {
    return ref.read(socialServiceProvider).getFriends();
  }

  Future<void> removeFriend(String userId) async {
    final service = ref.read(socialServiceProvider);
    await service.removeFriend(userId);
    state = AsyncData(
      state.value?.where((f) => f.userId != userId).toList() ?? [],
    );
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(socialServiceProvider).getFriends(),
    );
  }
}
