import 'package:cross_file/cross_file.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/providers.dart';
import '../../../capture/data/capture_service.dart';
import '../../../location/data/location_service.dart';
import '../../../social/domain/friend.dart';
import '../../../social/presentation/providers/friend_notifier.dart';
import '../../data/send_service.dart';

/// Displays the friend list and lets the user pick recipients
/// before sending the captured photo.
class RecipientSelectorScreen extends ConsumerStatefulWidget {
  const RecipientSelectorScreen({
    super.key,
    required this.imageData,
  });

  /// Keys: 'image_path' (String), 'pet_id' (String?).
  final Map<String, dynamic> imageData;

  @override
  ConsumerState<RecipientSelectorScreen> createState() =>
      _RecipientSelectorScreenState();
}

class _RecipientSelectorScreenState
    extends ConsumerState<RecipientSelectorScreen> {
  final Set<String> _selectedIds = {};
  bool _sending = false;

  Future<void> _send() async {
    if (_selectedIds.isEmpty) return;
    setState(() => _sending = true);

    try {
      final dio = ref.read(dioProvider);
      final sendService = SendService(dio: dio);
      final captureService = CaptureService(dio: dio);

      final imagePath = widget.imageData['image_path'] as String;
      final petId = widget.imageData['pet_id'] as String?;

      final uploadUrl = await sendService.getUploadUrl('image/jpeg');
      final imageUrl = await captureService.uploadImage(
        XFile(imagePath),
        uploadUrl,
      );

      final location = await LocationService().getCurrentPayload();

      await sendService.sendPost(
        imageUrl: imageUrl,
        recipientIds: _selectedIds.toList(),
        petId: petId,
        locationPayload: location,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã gửi ảnh!')),
        );
        context.go('/feed');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Lỗi: $e')));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final friendsAsync = ref.watch(friendNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chọn người nhận'),
        actions: [
          TextButton(
            onPressed: _sending ? null : _send,
            child: _sending
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Gửi'),
          ),
        ],
      ),
      body: friendsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Lỗi: $e')),
        data: (friends) => _FriendCheckList(
          friends: friends,
          selectedIds: _selectedIds,
          onToggle: (id) => setState(() {
            if (_selectedIds.contains(id)) {
              _selectedIds.remove(id);
            } else {
              _selectedIds.add(id);
            }
          }),
        ),
      ),
    );
  }
}

class _FriendCheckList extends StatelessWidget {
  const _FriendCheckList({
    required this.friends,
    required this.selectedIds,
    required this.onToggle,
  });

  final List<Friend> friends;
  final Set<String> selectedIds;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    if (friends.isEmpty) {
      return const Center(child: Text('Chưa có bạn bè để gửi.'));
    }
    return ListView.builder(
      itemCount: friends.length,
      itemBuilder: (_, i) {
        final friend = friends[i];
        return CheckboxListTile(
          title: Text(friend.displayName),
          value: selectedIds.contains(friend.userId),
          onChanged: (_) => onToggle(friend.userId),
          secondary: friend.avatarUrl != null
              ? CircleAvatar(
                  backgroundImage: NetworkImage(friend.avatarUrl!),
                )
              : const CircleAvatar(child: Icon(Icons.person)),
        );
      },
    );
  }
}
