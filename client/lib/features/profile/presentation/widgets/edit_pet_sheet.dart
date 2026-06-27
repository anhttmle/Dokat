import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/pet_profile.dart';
import '../providers/pet_notifier.dart';

/// Bottom sheet for editing an existing pet profile.
class EditPetSheet extends ConsumerStatefulWidget {
  const EditPetSheet({super.key, required this.pet});

  final PetProfile pet;

  @override
  ConsumerState<EditPetSheet> createState() => _EditPetSheetState();
}

class _EditPetSheetState extends ConsumerState<EditPetSheet> {
  late final TextEditingController _nameController;
  late String _species;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _nameController =
        TextEditingController(text: widget.pet.name);
    _species = widget.pet.species;
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) return;
    setState(() => _loading = true);
    await ref.read(petNotifierProvider.notifier).updatePet(
      widget.pet.petId,
      {'name': name, 'species': _species},
    );
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
            'Chỉnh sửa thú cưng',
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
                : const Text('Lưu'),
          ),
        ],
      ),
    );
  }
}
