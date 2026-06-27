import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../providers/friend_notifier.dart';

/// Shows the user's own QR code for others to scan.
class AddFriendScreen extends ConsumerWidget {
  const AddFriendScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final otpAsync = ref.watch(_qrOtpProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Thêm bạn'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            onPressed: () => context.push('/friends/scan'),
          ),
        ],
      ),
      body: Center(
        child: otpAsync.when(
          loading: () => const CircularProgressIndicator(),
          error: (e, _) => Text('Lỗi: $e'),
          data: (otp) => Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'Cho bạn bè quét mã QR này',
                style: TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 24),
              QrImageView(
                data: otp,
                version: QrVersions.auto,
                size: 240,
              ),
              const SizedBox(height: 24),
              const Text(
                'Mã có hiệu lực trong 5 phút',
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

final _qrOtpProvider = FutureProvider<String>((ref) async {
  return ref.read(socialServiceProvider).generateQrOtp();
});
