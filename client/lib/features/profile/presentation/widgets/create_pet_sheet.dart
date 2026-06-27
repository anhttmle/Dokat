import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/pet_notifier.dart';

/// Bottom sheet for creating a new pet profile.
class CreatePetSheet extends ConsumerStatefulWidget {
  const CreatePetSheet({super.key});

  @override
  ConsumerState<CreatePetSheet> createState() => _CreatePetSheetState();
}

class _CreatePetSheetState extends ConsumerState<CreatePetSheet> {
  final _nameController = TextEditingController();
  String _species = 'dog';
  bool _loading = false;

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) return;
    setState(() => _loading = true);
    await ref.read(petNotifierProvider.notifier).createPet({
      'name': name,
      'species': _species,
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
            'Thêm thú cưng',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _nameController,
            decoration: const InputDecoration(labelText: 'Tên'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _species,
            items: const [
              DropdownMenuItem(value: 'dog', child: Text('Chó')),
              DropdownMenuItem(value: 'cat', child: Text('Mèo')),
            ],
            onChanged: (v) => setState(() => _species = v ?? 'dog'),
            decoration: const InputDecoration(labelText: 'Loài'),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const CircularProgressIndicator()
                : const Text('Tạo'),
          ),
        ],
      ),
    );
  }
}
