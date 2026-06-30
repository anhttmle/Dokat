import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

/// Global [Dio] provider — single instance for the entire app.
final dioProvider = Provider<Dio>((ref) => createApiClient());
