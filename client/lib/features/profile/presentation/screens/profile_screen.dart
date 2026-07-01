import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants.dart';
import '../../domain/pet_profile.dart';
import '../providers/pet_notifier.dart';
import '../providers/profile_notifier.dart';
import '../widgets/create_pet_sheet.dart';
import '../widgets/edit_owner_sheet.dart';
import '../widgets/edit_pet_sheet.dart';

/// Displays the owner profile and list of pets.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(profileNotifierProvider);
    final petsAsync = ref.watch(petNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Hồ sơ'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            onPressed: () => _editProfile(context, ref),
          ),
        ],
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Lỗi: $e')),
        data: (profile) => ListView(
          children: [
            _ProfileHeader(
              displayName: profile?.displayName ?? '',
              avatarUrl: profile?.avatarUrl,
            ),
            const Divider(),
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 8,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Thú cưng',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  IconButton(
                    icon: const Icon(Icons.add),
                    tooltip: petsAsync.maybeWhen(
                      data: (pets) => pets.length >= Constants.maxPetsFree
                          ? 'Đã đạt giới hạn hồ sơ thú cưng'
                          : 'Thêm thú cưng',
                      orElse: () => 'Thêm thú cưng',
                    ),
                    onPressed: petsAsync.maybeWhen(
                      data: (pets) => pets.length >= Constants.maxPetsFree
                          ? null
                          : () => _addPet(context, ref),
                      orElse: () => () => _addPet(context, ref),
                    ),
                  ),
                ],
              ),
            ),
            petsAsync.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Lỗi: $e')),
              data: (pets) {
                final atPetLimit = pets.length >= Constants.maxPetsFree;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (atPetLimit)
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 4,
                        ),
                        child: Text(
                          'Mỗi tài khoản chỉ có ${Constants.maxPetsFree} '
                          'hồ sơ thú cưng. Sửa hồ sơ hiện có để đổi loài.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ...pets.map(
                      (pet) => ListTile(
                        leading: pet.avatarUrl != null
                            ? CircleAvatar(
                                backgroundImage:
                                    NetworkImage(pet.avatarUrl!),
                              )
                            : const CircleAvatar(
                                child: Icon(Icons.pets),
                              ),
                        title: Text(pet.name),
                        subtitle: Text(
                          pet.species == 'cat' ? 'Mèo' : 'Chó',
                        ),
                        trailing: IconButton(
                          icon: const Icon(Icons.edit_outlined),
                          tooltip: 'Chỉnh sửa',
                          onPressed: () => _editPet(context, pet),
                        ),
                        onTap: () => context.push(
                          '/settings/profile/pet/${pet.petId}',
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  void _editProfile(BuildContext context, WidgetRef ref) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const EditOwnerSheet(),
    );
  }

  void _addPet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const CreatePetSheet(),
    );
  }

  void _editPet(BuildContext context, PetProfile pet) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (_) => EditPetSheet(pet: pet),
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({
    required this.displayName,
    this.avatarUrl,
  });

  final String displayName;
  final String? avatarUrl;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          CircleAvatar(
            radius: 48,
            backgroundImage:
                avatarUrl != null ? NetworkImage(avatarUrl!) : null,
            child: avatarUrl == null ? const Icon(Icons.person, size: 48) : null,
          ),
          const SizedBox(height: 12),
          Text(
            displayName,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
        ],
      ),
    );
  }
}
