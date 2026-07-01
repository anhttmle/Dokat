import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/core/api_client.dart';
import 'package:dokat/core/session_storage.dart';
import 'package:dokat/features/auth/data/auth_service.dart';

import 'auth_service_test.mocks.dart';

@GenerateMocks([Dio, SessionStorage])
void main() {
  late MockDio mockDio;
  late MockSessionStorage mockStorage;
  late AuthService service;

  setUp(() {
    mockDio = MockDio();
    mockStorage = MockSessionStorage();
    service = AuthService(dio: mockDio, storage: mockStorage);
  });

  group('AuthService.signInWithDeviceId', () {
    test('stores JWT and user_id from POST /auth/token', () async {
      when(mockStorage.read(kDeviceIdKey))
          .thenAnswer((_) async => 'device-abc');
      when(
        mockDio.post<Map<String, dynamic>>(
          '/auth/token',
          data: anyNamed('data'),
        ),
      ).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/auth/token'),
          data: {
            'access_token': 'jwt-token',
            'user_id': 'user-uuid',
          },
        ),
      );

      await service.signInWithDeviceId();

      verify(mockStorage.write(kJwtTokenKey, 'jwt-token')).called(1);
      verify(mockStorage.write(kJwtUserIdKey, 'user-uuid')).called(1);
    });

    test('generates device_id when none stored', () async {
      when(mockStorage.read(kDeviceIdKey)).thenAnswer((_) async => null);
      when(mockStorage.write(any, any)).thenAnswer((_) async {});
      when(
        mockDio.post<Map<String, dynamic>>(
          '/auth/token',
          data: anyNamed('data'),
        ),
      ).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/auth/token'),
          data: {
            'access_token': 'jwt-token',
            'user_id': 'user-uuid',
          },
        ),
      );

      await service.signInWithDeviceId();

      verify(
        mockStorage.write(
          kDeviceIdKey,
          argThat(isNotEmpty),
        ),
      ).called(1);
    });
  });

  group('AuthService.hasJwtSession', () {
    test('returns true when jwt_token exists', () async {
      when(mockStorage.read(kJwtTokenKey))
          .thenAnswer((_) async => 'token');

      expect(await service.hasJwtSession(), isTrue);
    });

    test('returns false when jwt_token is absent', () async {
      when(mockStorage.read(kJwtTokenKey)).thenAnswer((_) async => null);

      expect(await service.hasJwtSession(), isFalse);
    });
  });
}
