import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../providers/friend_notifier.dart';

/// Scans a QR code and submits it to add a friend.
class QRScannerScreen extends ConsumerStatefulWidget {
  const QRScannerScreen({super.key});

  @override
  ConsumerState<QRScannerScreen> createState() => _QRScannerScreenState();
}

class _QRScannerScreenState extends ConsumerState<QRScannerScreen> {
  bool _scanned = false;

  void _onDetect(BarcodeCapture capture) async {
    if (_scanned) return;
    final barcodes = capture.barcodes;
    if (barcodes.isEmpty) return;
    final otp = barcodes.first.rawValue;
    if (otp == null) return;

    setState(() => _scanned = true);

    try {
      await ref.read(socialServiceProvider).scanQrOtp(otp);
      await ref.read(friendNotifierProvider.notifier).refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Kết bạn thành công!')),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $e')),
        );
        setState(() => _scanned = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) {
      return Scaffold(
        appBar: AppBar(title: const Text('Quét QR')),
        body: const Center(
          child: Text('QR scanner chỉ hỗ trợ trên ứng dụng mobile.'),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Quét QR')),
      body: Stack(
        children: [
          MobileScanner(onDetect: _onDetect),
          if (_scanned)
            const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}
