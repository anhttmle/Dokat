import 'package:flutter/material.dart';

import '../../../../shared/utils/relative_time.dart';
import '../../domain/history_item.dart';

/// Renders a list of [SentHistoryItem] objects.
class SentHistoryList extends StatelessWidget {
  const SentHistoryList({super.key, required this.items});

  final List<SentHistoryItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const Center(child: Text('Chưa có ảnh nào.'));
    }
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (_, i) {
        final item = items[i];
        return ListTile(
          leading: SizedBox(
            width: 56,
            height: 56,
            child: Image.network(item.cdnUrl, fit: BoxFit.cover),
          ),
          title: Text(relativeTime(item.createdAt)),
          subtitle: Text(
            '${item.seenCount}/${item.recipientCount} đã xem',
          ),
        );
      },
    );
  }
}

/// Renders a list of [ReceivedHistoryItem] objects.
class ReceivedHistoryList extends StatelessWidget {
  const ReceivedHistoryList({super.key, required this.items});

  final List<ReceivedHistoryItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const Center(child: Text('Chưa có ảnh nào.'));
    }
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (_, i) {
        final item = items[i];
        return ListTile(
          leading: SizedBox(
            width: 56,
            height: 56,
            child: Image.network(item.cdnUrl, fit: BoxFit.cover),
          ),
          title: Text(item.senderDisplayName ?? 'Ẩn danh'),
          subtitle: Text(relativeTime(item.createdAt)),
          trailing: item.petName != null ? Text(item.petName!) : null,
          tileColor: item.seen ? null : Theme.of(context).highlightColor,
        );
      },
    );
  }
}
