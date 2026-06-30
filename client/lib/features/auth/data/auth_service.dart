import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../../core/api_client.dart';

/// Storage key for the persistent device identifier.
const String kDeviceIdKey = 'device_id';

/// Storage key for the user UUID returned by POST /auth/token.
const String kJwtUserIdKey = 'jwt_user_id';

/// Handles backend JWT authentication via POST /auth/token.
class AuthService {
  AuthService({
    required Dio dio,
    FlutterSecureStorage? secureStorage,
  })  : _dio = dio,
        _storage = secureStorage ?? const FlutterSecureStorage();

  final Dio _dio;
  final FlutterSecureStorage _storage;

  /// Signs in using a persistent device ID and POST /auth/token.
  ///
  /// Generates a new UUID [device_id] on first call and persists it.
  /// Subsequent calls reuse the same [device_id] → same backend user.
  Future<void> signInWithDeviceId() async {
    String? deviceId = await _storage.read(key: kDeviceIdKey);
    if (deviceId == null) {
      deviceId = _generateUuid();
      await _storage.write(key: kDeviceIdKey, value: deviceId);
    }

    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/token',
      data: {'device_id': deviceId},
    );

    final data = response.data!;
    final token = data['access_token'] as String;
    final userId = data['user_id'] as String;

    await _storage.write(key: kJwtTokenKey, value: token);
    await _storage.write(key: kJwtUserIdKey, value: userId);
  }

  /// Reads the stored JWT user ID.
  Future<String?> getJwtUserId() => _storage.read(key: kJwtUserIdKey);

  /// Returns true if a JWT token is present in secure storage.
  Future<bool> hasJwtSession() async {
    final token = await _storage.read(key: kJwtTokenKey);
    return token != null;
  }

  /// Clears the stored JWT token and user ID (keeps device_id).
  Future<void> clearJwtSession() async {
    await _storage.delete(key: kJwtTokenKey);
    await _storage.delete(key: kJwtUserIdKey);
  }

  /// Signs out locally and obtains a fresh JWT for the same device.
  Future<void> signOut() async {
    await clearJwtSession();
    await signInWithDeviceId();
  }

  /// Generates a random UUID v4 string without external packages.
  static String _generateUuid() {
    final rng = Random.secure();
    final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    String hex(int b) => b.toRadixString(16).padLeft(2, '0');
    return [
      bytes.sublist(0, 4).map(hex).join(),
      bytes.sublist(4, 6).map(hex).join(),
      bytes.sublist(6, 8).map(hex).join(),
      bytes.sublist(8, 10).map(hex).join(),
      bytes.sublist(10, 16).map(hex).join(),
    ].join('-');
  }
}
