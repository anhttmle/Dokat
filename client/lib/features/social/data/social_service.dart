import 'package:dio/dio.dart';

import '../domain/friend.dart';

/// HTTP service for social graph (friends + QR) endpoints.
class SocialService {
  SocialService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// POST /friends/qr/generate
  ///
  /// Returns the token string to encode into a QR code.
  Future<String> generateQrToken() async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/friends/qr/generate',
    );
    return response.data!['token'] as String;
  }

  /// POST /friends/qr/scan
  ///
  /// [token] is the value decoded from the scanned QR code.
  Future<void> scanQrToken(String token) async {
    await _dio.post<void>(
      '/friends/qr/scan',
      data: {'token': token},
    );
  }

  /// GET /friends
  Future<List<Friend>> getFriends() async {
    final response = await _dio.get<dynamic>('/friends');
    final data = response.data;
    final list =
        data is Map ? (data['friends'] as List?) ?? [] : (data as List?) ?? [];
    return list
        .cast<Map<String, dynamic>>()
        .map(Friend.fromJson)
        .toList();
  }

  /// DELETE /friends/:friendUserId
  Future<void> removeFriend(String friendUserId) async {
    await _dio.delete<void>('/friends/$friendUserId');
  }

  /// PUT /friends/fcm-token
  Future<void> updateFcmToken(String token) async {
    await _dio.put<void>(
      '/friends/fcm-token',
      data: {'fcm_token': token},
    );
  }
}
