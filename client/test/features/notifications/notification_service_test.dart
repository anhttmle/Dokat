import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/notifications/data/notification_service.dart';

import 'notification_service_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late NotificationService service;

  setUp(() {
    mockDio = MockDio();
    service = NotificationService(dio: mockDio);
  });

  test('registerToken is a no-op', () async {
    await service.registerToken();
    verifyZeroInteractions(mockDio);
  });

  test('getPreferences returns map from backend', () async {
    when(mockDio.get<Map<String, dynamic>>('/notifications/preferences'))
        .thenAnswer(
      (_) async => Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: '/notifications/preferences'),
        data: {'feeding': true, 'sleeping': false},
      ),
    );

    final prefs = await service.getPreferences();

    expect(prefs['feeding'], isTrue);
    expect(prefs['sleeping'], isFalse);
  });
}
