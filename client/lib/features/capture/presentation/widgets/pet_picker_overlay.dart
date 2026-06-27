import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../profile/domain/pet_profile.dart';
import '../../../profile/presentation/providers/pet_notifier.dart';
import 'pet_selector_chip.dart';

/// Overlay shown on top of the camera viewfinder to pick a pet.
class PetPickerOverlay extends ConsumerStatefulWidget {
  const PetPickerOverlay({
    super.key,
    required this.onPetSelected,
  });

  final ValueChanged<PetProfile?> onPetSelected;

  @override
  ConsumerState<PetPickerOverlay> createState() =>
      _PetPickerOverlayState();
}

class _PetPickerOverlayState extends ConsumerState<PetPickerOverlay> {
  String? _selectedPetId;

  @override
  Widget build(BuildContext context) {
    final petsAsync = ref.watch(petNotifierProvider);

    return petsAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (pets) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          children: pets.map((pet) {
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: PetSelectorChip(
                pet: pet,
                selected: _selectedPetId == pet.petId,
                onTap: () {
                  setState(() {
                    _selectedPetId =
                        _selectedPetId == pet.petId ? null : pet.petId;
                  });
                  widget.onPetSelected(
                    _selectedPetId == null
                        ? null
                        : pets.firstWhere(
                            (p) => p.petId == _selectedPetId,
                          ),
                  );
                },
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}
