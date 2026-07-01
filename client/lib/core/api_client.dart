import 'package:dio/dio.dart';

import 'api_config.dart';
import 'session_storage.dart';

/// Storage key for the JWT issued by POST /auth/token.
const String kJwtTokenKey = 'jwt_token';

/// Creates and configures the shared [Dio] instance.
///
/// Injects `Authorization: Bearer <jwt>` from [SessionStorage].
Dio createApiClient({required SessionStorage storage}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: resolveApiBaseUrl(),
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final jwt = await storage.read(kJwtTokenKey);
        if (jwt != null) {
          options.headers['Authorization'] = 'Bearer $jwt';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        handler.next(error);
      },
    ),
  );

  return dio;
}
