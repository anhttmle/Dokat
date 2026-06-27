import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/notifications/data/notification_service.dart';

import 'notification_service_test.mocks.dart';

@GenerateMocks([Dio, FirebaseMessaging, NotificationSettings])
void main() {
  late MockDio mockDio;
  late MockFirebaseMessaging mockMessaging;
  late NotificationService service;

  setUp(() {
    mockDio = MockDio();
    mockMessaging = MockFirebaseMessaging();
    service = NotificationService(dio: mockDio, messaging: mockMessaging);
  });

  test('getPreferences parses prefs map', () async {
    when(
      mockDio.get<Map<String, dynamic>>(
        '/notifications/preferences',
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(
          path: '/notifications/preferences',
        ),
        data: {'new_photo': true, 'friend_request': false},
        statusCode: 200,
      ),
    );

    final prefs = await service.getPreferences();
    expect(prefs['new_photo'], isTrue);
    expect(prefs['friend_request'], isFalse);
  });
}
