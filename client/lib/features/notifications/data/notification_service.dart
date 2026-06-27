import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

/// Handles FCM token registration and notification preferences.
class NotificationService {
  NotificationService({
    required Dio dio,
    FirebaseMessaging? messaging,
  })  : _dio = dio,
        _messaging = messaging ?? FirebaseMessaging.instance;

  final Dio _dio;
  final FirebaseMessaging _messaging;

  /// Requests notification permission and registers the FCM token
  /// with the backend via PUT /friends/fcm-token.
  Future<void> registerToken() async {
    final settings = await _messaging.requestPermission();
    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      return;
    }
    final token = await _messaging.getToken();
    if (token == null) return;
    await _dio.put<void>(
      '/friends/fcm-token',
      data: {'fcm_token': token},
    );
  }

  /// GET /notifications/preferences
  ///
  /// Returns a map of preference type → enabled.
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
