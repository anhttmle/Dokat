import 'package:dio/dio.dart';

import '../domain/friend.dart';

/// HTTP service for social graph (friends + QR) endpoints.
class SocialService {
  SocialService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// POST /friends/qr/generate
  ///
  /// Returns the OTP string to encode into a QR code.
  Future<String> generateQrOtp() async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/friends/qr/generate',
    );
    return response.data!['otp'] as String;
  }

  /// POST /friends/qr/scan
  ///
  /// [otp] is the value decoded from the scanned QR code.
  Future<void> scanQrOtp(String otp) async {
    await _dio.post<void>(
      '/friends/qr/scan',
      data: {'otp': otp},
    );
  }

  /// GET /friends
  Future<List<Friend>> getFriends() async {
    final response = await _dio.get<List<dynamic>>('/friends');
    return (response.data ?? [])
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
