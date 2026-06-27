import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/seen_service.dart';

/// Displays the list of users who have seen a specific post.
class SeenByList extends ConsumerWidget {
  const SeenByList({super.key, required this.postId});

  final String postId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final seenByAsync = ref.watch(_seenByProvider(postId));

    return seenByAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Text('Lỗi: $e'),
      data: (names) => names.isEmpty
          ? const Text('Chưa ai xem.')
          : Wrap(
              spacing: 8,
              children: names
                  .map((name) => Chip(label: Text(name)))
                  .toList(),
            ),
    );
  }
}

final _seenByProvider =
    FutureProvider.family<List<String>, String>((ref, postId) async {
  return SeenService(dio: ref.read(dioProvider)).getSeenBy(postId);
});
