import 'package:dio/dio.dart';

/// Handles notification preferences via backend API.
///
/// Push token registration (FCM) is not supported — auth is backend-only.
class NotificationService {
  NotificationService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// No-op: push notifications require FCM which is not used.
  Future<void> registerToken() async {}

  /// GET /notifications/preferences
  Future<Map<String, bool>> getPreferences() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/notifications/preferences',
    );
    return (response.data ?? {}).cast<String, bool>();
  }

  /// PUT /notifications/preferences/:type
  Future<void> updatePreference(String type, {required bool enabled}) async {
    await _dio.put<void>(
      '/notifications/preferences/$type',
      data: {'enabled': enabled},
    );
  }
}
