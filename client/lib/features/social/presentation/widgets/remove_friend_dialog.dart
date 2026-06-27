import 'package:flutter/material.dart';

/// Confirmation dialog before removing a friend.
class RemoveFriendDialog extends StatelessWidget {
  const RemoveFriendDialog({
    super.key,
    required this.displayName,
    required this.onConfirm,
  });

  final String displayName;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Xóa bạn bè'),
      content: Text('Bạn có chắc muốn xóa $displayName khỏi danh sách?'),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: () {
            Navigator.of(context).pop();
            onConfirm();
          },
          child: const Text('Xóa'),
        ),
      ],
    );
  }
}
