import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/settings/data/settings_service.dart';

import 'settings_service_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late SettingsService service;

  setUp(() {
    mockDio = MockDio();
    service = SettingsService(dio: mockDio);
  });

  test('blockUser calls POST /users/block', () async {
    when(
      mockDio.post<void>('/users/block', data: anyNamed('data')),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/users/block'),
        statusCode: 201,
      ),
    );

    await service.blockUser('u2');
    verify(
      mockDio.post<void>(
        '/users/block',
        data: argThat(
          containsPair('target_user_id', 'u2'),
          named: 'data',
        ),
      ),
    ).called(1);
  });

  test('unlinkProvider calls DELETE /users/providers/:provider', () async {
    when(mockDio.delete<void>('/users/providers/google'))
        .thenAnswer(
      (_) async => Response(
        requestOptions:
            RequestOptions(path: '/users/providers/google'),
        statusCode: 204,
      ),
    );

    await service.unlinkProvider('google');
    verify(mockDio.delete<void>('/users/providers/google')).called(1);
  });
}
