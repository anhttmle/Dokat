import 'dart:math';

import 'package:dio/dio.dart';

import '../../../../core/api_client.dart';
import '../../../../core/session_storage.dart';

/// Storage key for the persistent device identifier.
const String kDeviceIdKey = 'device_id';

/// Storage key for the user UUID returned by POST /auth/token.
const String kJwtUserIdKey = 'jwt_user_id';

/// Handles backend JWT authentication via POST /auth/token.
class AuthService {
  AuthService({
    required Dio dio,
    required SessionStorage storage,
  })  : _dio = dio,
        _storage = storage;

  final Dio _dio;
  final SessionStorage _storage;

  /// Signs in using a persistent device ID and POST /auth/token.
  ///
  /// Generates a new UUID [device_id] on first call and persists it.
  /// Subsequent calls reuse the same [device_id] → same backend user.
  Future<void> signInWithDeviceId() async {
    String? deviceId = await _storage.read(kDeviceIdKey);
    if (deviceId == null) {
      deviceId = _generateUuid();
      await _storage.write(kDeviceIdKey, deviceId);
    }

    final response = await _dio.post<Map<String, dynamic>>(
      '/auth/token',
      data: {'device_id': deviceId},
    );

    final data = response.data;
    if (data == null) {
      throw StateError('POST /auth/token returned null body');
    }
    final token = data['access_token'] as String;
    final userId = data['user_id'] as String;

    await _storage.write(kJwtTokenKey, token);
    await _storage.write(kJwtUserIdKey, userId);
  }

  /// Reads the stored JWT user ID.
  Future<String?> getJwtUserId() => _storage.read(kJwtUserIdKey);

  /// Returns true if a JWT token is present in storage.
  Future<bool> hasJwtSession() async {
    final token = await _storage.read(kJwtTokenKey);
    return token != null;
  }

  /// Clears the stored JWT token and user ID (keeps device_id).
  Future<void> clearJwtSession() async {
    await _storage.delete(kJwtTokenKey);
    await _storage.delete(kJwtUserIdKey);
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
