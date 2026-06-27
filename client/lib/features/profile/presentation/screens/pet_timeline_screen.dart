import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers.dart';
import '../../data/pet_service.dart';

/// Shows the photo timeline for a specific pet.
class PetTimelineScreen extends ConsumerWidget {
  const PetTimelineScreen({super.key, required this.petId});

  final String petId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final photosAsync = ref.watch(_petPhotosProvider(petId));

    return Scaffold(
      appBar: AppBar(title: const Text('Timeline')),
      body: photosAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Lỗi: $e')),
        data: (photos) => photos.isEmpty
            ? const Center(child: Text('Chưa có ảnh nào.'))
            : GridView.builder(
                padding: const EdgeInsets.all(4),
                gridDelegate:
                    const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3,
                  crossAxisSpacing: 4,
                  mainAxisSpacing: 4,
                ),
                itemCount: photos.length,
                itemBuilder: (_, i) => Image.network(
                  photos[i],
                  fit: BoxFit.cover,
                ),
              ),
      ),
    );
  }
}

final _petPhotosProvider =
    FutureProvider.family<List<String>, String>((ref, petId) async {
  final petService =
      PetService(dio: ref.read(dioProvider));
  return petService.getPetPhotos(petId);
});
