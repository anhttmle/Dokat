import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/providers.dart';
import 'core/session_storage.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = await createSessionStorage();
  runApp(
    ProviderScope(
      overrides: [sessionStorageProvider.overrideWithValue(storage)],
      child: const DokatApp(),
    ),
  );
}
