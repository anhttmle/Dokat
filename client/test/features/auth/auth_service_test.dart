import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/core/api_client.dart';
import 'package:dokat/features/auth/data/auth_service.dart';

import 'auth_service_test.mocks.dart';

@GenerateMocks([Dio, FlutterSecureStorage])
void main() {
  late MockDio mockDio;
  late MockFlutterSecureStorage mockStorage;
  late AuthService service;

  setUp(() {
    mockDio = MockDio();
    mockStorage = MockFlutterSecureStorage();
    service = AuthService(dio: mockDio, secureStorage: mockStorage);
  });

  group('AuthService.signInWithDeviceId', () {
    test('stores JWT and user_id from POST /auth/token', () async {
      when(mockStorage.read(key: kDeviceIdKey))
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

      verify(mockStorage.write(key: kJwtTokenKey, value: 'jwt-token'))
          .called(1);
      verify(mockStorage.write(key: kJwtUserIdKey, value: 'user-uuid'))
          .called(1);
    });

    test('generates device_id when none stored', () async {
      when(mockStorage.read(key: kDeviceIdKey)).thenAnswer((_) async => null);
      when(mockStorage.write(key: anyNamed('key'), value: anyNamed('value')))
          .thenAnswer((_) async {});
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
          key: kDeviceIdKey,
          value: argThat(isNotEmpty, named: 'value'),
        ),
      ).called(1);
    });
  });

  group('AuthService.hasJwtSession', () {
    test('returns true when jwt_token exists', () async {
      when(mockStorage.read(key: kJwtTokenKey))
          .thenAnswer((_) async => 'token');

      expect(await service.hasJwtSession(), isTrue);
    });

    test('returns false when jwt_token is absent', () async {
      when(mockStorage.read(key: kJwtTokenKey))
          .thenAnswer((_) async => null);

      expect(await service.hasJwtSession(), isFalse);
    });
  });
}
