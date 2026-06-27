import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/settings_service.dart';

/// Dialog to report a user with a selectable reason.
class ReportDialog extends ConsumerStatefulWidget {
  const ReportDialog({
    super.key,
    required this.targetUserId,
    required this.displayName,
  });

  final String targetUserId;
  final String displayName;

  @override
  ConsumerState<ReportDialog> createState() => _ReportDialogState();
}

class _ReportDialogState extends ConsumerState<ReportDialog> {
  String _reason = 'spam';
  bool _submitting = false;

  static const _reasons = {
    'spam': 'Spam',
    'inappropriate': 'Nội dung không phù hợp',
    'harassment': 'Quấy rối',
    'other': 'Khác',
  };

  Future<void> _submit() async {
    setState(() => _submitting = true);
    await SettingsService(dio: ref.read(dioProvider))
        .reportUser(widget.targetUserId, _reason);
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Báo cáo ${widget.displayName}'),
      content: RadioGroup<String>(
        groupValue: _reason,
        onChanged: (v) => setState(() => _reason = v ?? _reason),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: _reasons.entries.map((e) {
            return RadioListTile<String>(
              title: Text(e.value),
              value: e.key,
            );
          }).toList(),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: _submitting ? null : _submit,
          child: _submitting
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Gửi'),
        ),
      ],
    );
  }
}
