import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/friend_notifier.dart';
import '../widgets/remove_friend_dialog.dart';

/// Displays the current user's friend list.
class FriendListScreen extends ConsumerWidget {
  const FriendListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final friendsAsync = ref.watch(friendNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Bạn bè'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_add_outlined),
            onPressed: () => context.push('/friends/add'),
          ),
        ],
      ),
      body: friendsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Lỗi: $e')),
        data: (friends) => friends.isEmpty
            ? const Center(child: Text('Chưa có bạn bè nào.'))
            : ListView.builder(
                itemCount: friends.length,
                itemBuilder: (context, i) {
                  final friend = friends[i];
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundImage: friend.avatarUrl != null
                          ? NetworkImage(friend.avatarUrl!)
                          : null,
                      child: friend.avatarUrl == null
                          ? const Icon(Icons.person)
                          : null,
                    ),
                    title: Text(friend.displayName),
                    trailing: IconButton(
                      icon: const Icon(Icons.more_vert),
                      onPressed: () => _showRemoveDialog(
                        context,
                        ref,
                        friend.userId,
                        friend.displayName,
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }

  void _showRemoveDialog(
    BuildContext context,
    WidgetRef ref,
    String userId,
    String displayName,
  ) {
    showDialog<void>(
      context: context,
      builder: (_) => RemoveFriendDialog(
        displayName: displayName,
        onConfirm: () =>
            ref.read(friendNotifierProvider.notifier).removeFriend(userId),
      ),
    );
  }
}
