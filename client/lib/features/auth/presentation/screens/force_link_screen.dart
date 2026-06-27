import 'package:flutter/material.dart';

import '../widgets/link_account_sheet.dart';

/// Full-screen, non-dismissable screen shown to guests who
/// have been using the app for >= 7 days without linking OAuth.
class ForceLinkScreen extends StatelessWidget {
  const ForceLinkScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.lock_outline, size: 64),
              const SizedBox(height: 24),
              Text(
                'Liên kết tài khoản bắt buộc',
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              const Text(
                'Tài khoản Guest của bạn đã tồn tại hơn 7 ngày. '
                'Vui lòng liên kết một tài khoản để tiếp tục sử dụng Dokat.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              // No onDismiss — user cannot close this screen.
              const LinkAccountSheet(),
            ],
          ),
        ),
      ),
    );
  }
}
