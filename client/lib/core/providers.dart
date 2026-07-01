import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'session_storage.dart';

/// Holds the [SessionStorage] singleton initialised in [main].
///
/// Must be overridden via [ProviderScope] before any consumer reads it.
final sessionStorageProvider = Provider<SessionStorage>(
  (_) => throw UnimplementedError('sessionStorageProvider not overridden'),
);

/// Global [Dio] provider — single instance for the entire app.
final dioProvider = Provider<Dio>(
  (ref) => createApiClient(storage: ref.read(sessionStorageProvider)),
);
