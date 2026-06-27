import 'package:flutter/material.dart';

/// Full-screen semi-transparent overlay with a centered [CircularProgressIndicator].
class LoadingOverlay extends StatelessWidget {
  const LoadingOverlay({super.key});

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Color(0x66000000),
      child: Center(child: CircularProgressIndicator()),
    );
  }
}
