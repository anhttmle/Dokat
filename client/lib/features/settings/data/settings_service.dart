import 'package:dio/dio.dart';

/// HTTP service for settings (block/report/unlink/logout).
class SettingsService {
  SettingsService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// DELETE /users/providers/:provider
  ///
  /// Unlinks an OAuth provider from the user's account.
  Future<void> unlinkProvider(String provider) async {
    await _dio.delete<void>('/users/providers/$provider');
  }

  /// POST /users/block
  Future<void> blockUser(String targetUserId) async {
    await _dio.post<void>(
      '/users/block',
      data: {'target_user_id': targetUserId},
    );
  }

  /// GET /users/block
  ///
  /// Returns a list of blocked user IDs.
  Future<List<String>> getBlockList() async {
    final response = await _dio.get<List<dynamic>>('/users/block');
    return (response.data ?? []).cast<String>();
  }

  /// DELETE /users/block/:userId
  Future<void> unblockUser(String userId) async {
    await _dio.delete<void>('/users/block/$userId');
  }

  /// POST /users/report
  Future<void> reportUser(
    String targetUserId,
    String reason,
  ) async {
    await _dio.post<void>(
      '/users/report',
      data: {'target_user_id': targetUserId, 'reason': reason},
    );
  }

  /// POST /users/logout — clears server-side session/token.
  Future<void> logout() async {
    await _dio.post<void>('/users/logout');
  }
}
