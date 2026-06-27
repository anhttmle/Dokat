import 'package:flutter/material.dart';

import '../../../feed/domain/post.dart';
import '../../../../shared/utils/relative_time.dart';

/// Renders a list of [Post] objects as history entries.
class HistoryList extends StatelessWidget {
  const HistoryList({super.key, required this.posts});

  final List<Post> posts;

  @override
  Widget build(BuildContext context) {
    if (posts.isEmpty) {
      return const Center(child: Text('Chưa có ảnh nào.'));
    }
    return ListView.builder(
      itemCount: posts.length,
      itemBuilder: (_, i) {
        final post = posts[i];
        return ListTile(
          leading: SizedBox(
            width: 56,
            height: 56,
            child: Image.network(post.imageUrl, fit: BoxFit.cover),
          ),
          title: Text(post.senderDisplayName),
          subtitle: Text(relativeTime(post.createdAt)),
          trailing: post.petName != null ? Text(post.petName!) : null,
        );
      },
    );
  }
}
