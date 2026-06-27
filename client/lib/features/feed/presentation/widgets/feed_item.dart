import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../../seen/data/seen_service.dart';
import '../../../seen/presentation/widgets/seen_by_list.dart';
import '../../domain/post.dart';
import '../../../../shared/utils/relative_time.dart';

/// A single item in the feed — shows pet photo, sender info,
/// and seen-by count. Marks the post as seen on first visibility.
class FeedItem extends ConsumerStatefulWidget {
  const FeedItem({super.key, required this.post});

  final Post post;

  @override
  ConsumerState<FeedItem> createState() => _FeedItemState();
}

class _FeedItemState extends ConsumerState<FeedItem> {
  late Post _post;

  @override
  void initState() {
    super.initState();
    _post = widget.post;
    if (!_post.seenByMe) _markSeen();
  }

  Future<void> _markSeen() async {
    await SeenService(dio: ref.read(dioProvider))
        .markSeen(_post.postId);
    if (mounted) {
      setState(() {
        _post = _post.copyWith(
          seenByMe: true,
          seenByCount: _post.seenByCount + 1,
        );
      });
    }
  }

  void _showSeenBy() {
    showModalBottomSheet<void>(
      context: context,
      builder: (_) => Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Đã xem',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            SeenByList(postId: _post.postId),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.hardEdge,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Image.network(
            _post.imageUrl,
            width: double.infinity,
            fit: BoxFit.cover,
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                CircleAvatar(
                  backgroundImage: _post.senderAvatarUrl != null
                      ? NetworkImage(_post.senderAvatarUrl!)
                      : null,
                  child: _post.senderAvatarUrl == null
                      ? const Icon(Icons.person)
                      : null,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _post.senderDisplayName,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (_post.petName != null)
                        Text(
                          _post.petName!,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      Text(
                        relativeTime(_post.createdAt),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.visibility_outlined, size: 18),
                  label: Text('${_post.seenByCount}'),
                  onPressed: _showSeenBy,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
