import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'constants.dart';

/// Storage key for the JWT issued by POST /auth/token.
const String kJwtTokenKey = 'jwt_token';

/// Creates and configures the shared [Dio] instance.
///
/// Injects `Authorization: Bearer <jwt>` from [FlutterSecureStorage].
Dio createApiClient({FlutterSecureStorage? secureStorage}) {
  final storage = secureStorage ?? const FlutterSecureStorage();

  final dio = Dio(
    BaseOptions(
      baseUrl: Constants.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final jwt = await storage.read(key: kJwtTokenKey);
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
