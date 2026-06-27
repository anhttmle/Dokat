import 'package:flutter/material.dart';

import '../../../profile/domain/pet_profile.dart';

/// A chip showing a pet's name; tappable to select/deselect it.
class PetSelectorChip extends StatelessWidget {
  const PetSelectorChip({
    super.key,
    required this.pet,
    required this.selected,
    required this.onTap,
  });

  final PetProfile pet;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilterChip(
      label: Text(pet.name),
      selected: selected,
      onSelected: (_) => onTap(),
      avatar: pet.avatarUrl != null
          ? CircleAvatar(backgroundImage: NetworkImage(pet.avatarUrl!))
          : const CircleAvatar(child: Icon(Icons.pets, size: 14)),
    );
  }
}
