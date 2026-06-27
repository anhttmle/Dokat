import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/pet_service.dart';
import '../../domain/pet_profile.dart';

final petServiceProvider = Provider<PetService>(
  (ref) => PetService(dio: ref.read(dioProvider)),
);

/// Provides the list of pets for the current user.
final petNotifierProvider =
    AsyncNotifierProvider<PetNotifier, List<PetProfile>>(
  PetNotifier.new,
);

class PetNotifier extends AsyncNotifier<List<PetProfile>> {
  @override
  Future<List<PetProfile>> build() async {
    return ref.read(petServiceProvider).getPets();
  }

  Future<void> createPet(Map<String, dynamic> data) async {
    final service = ref.read(petServiceProvider);
    final newPet = await service.createPet(data);
    state = AsyncData([...?state.value, newPet]);
  }

  Future<void> updatePet(
    String petId,
    Map<String, dynamic> fields,
  ) async {
    final service = ref.read(petServiceProvider);
    final updated = await service.updatePet(petId, fields);
    state = AsyncData(
      state.value
              ?.map((p) => p.petId == petId ? updated : p)
              .toList() ??
          [],
    );
  }
}
