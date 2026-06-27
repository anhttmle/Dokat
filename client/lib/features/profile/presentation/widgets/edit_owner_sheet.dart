import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/profile_notifier.dart';

/// Bottom sheet for editing the owner's display name and bio.
class EditOwnerSheet extends ConsumerStatefulWidget {
  const EditOwnerSheet({super.key});

  @override
  ConsumerState<EditOwnerSheet> createState() => _EditOwnerSheetState();
}

class _EditOwnerSheetState extends ConsumerState<EditOwnerSheet> {
  late final TextEditingController _nameController;
  late final TextEditingController _bioController;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    final profile = ref.read(profileNotifierProvider).value;
    _nameController =
        TextEditingController(text: profile?.displayName ?? '');
    _bioController = TextEditingController(text: profile?.bio ?? '');
  }

  @override
  void dispose() {
    _nameController.dispose();
    _bioController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) return;
    setState(() => _loading = true);
    await ref.read(profileNotifierProvider.notifier).updateProfile({
      'display_name': name,
      'bio': _bioController.text.trim(),
    });
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Chỉnh sửa hồ sơ',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'Tên hiển thị'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _bioController,
            decoration: const InputDecoration(labelText: 'Bio'),
            maxLines: 3,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const CircularProgressIndicator()
                : const Text('Lưu'),
          ),
        ],
      ),
    );
  }
}
