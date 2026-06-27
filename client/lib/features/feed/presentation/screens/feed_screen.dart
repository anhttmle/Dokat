import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/providers.dart';
import '../../data/feed_service.dart';
import '../../domain/post.dart';
import '../widgets/feed_item.dart';

final _feedProvider = FutureProvider.autoDispose<List<Post>>((ref) async {
  return FeedService(dio: ref.read(dioProvider)).getFeed();
});

/// Main feed screen — shows received pet photos with pull-to-refresh.
class FeedScreen extends ConsumerWidget {
  const FeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedAsync = ref.watch(_feedProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Dokat')),
      floatingActionButton: FloatingActionButton(
        heroTag: 'camera_fab',
        onPressed: () => context.push('/camera'),
        child: const Icon(Icons.camera_alt),
      ),
      body: feedAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Lỗi: $e')),
        data: (posts) => RefreshIndicator(
          onRefresh: () => ref.refresh(_feedProvider.future),
          child: posts.isEmpty
              ? const Center(
                  child: Text('Chưa có ảnh mới.'),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: posts.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (_, i) => FeedItem(post: posts[i]),
                ),
        ),
      ),
    );
  }
}
