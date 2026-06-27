import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'constants.dart';

/// Creates and configures the shared [Dio] instance.
///
/// Injects Firebase ID Token as Bearer token on every request.
Dio createApiClient({FirebaseAuth? auth}) {
  final firebaseAuth = auth ?? FirebaseAuth.instance;
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
        final user = firebaseAuth.currentUser;
        if (user != null) {
          final token = await user.getIdToken();
          options.headers['Authorization'] = 'Bearer $token';
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
