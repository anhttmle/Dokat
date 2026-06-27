import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/social/data/social_service.dart';
import 'package:dokat/features/social/domain/friend.dart';

import 'social_service_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late SocialService service;

  setUp(() {
    mockDio = MockDio();
    service = SocialService(dio: mockDio);
  });

  test('getFriends returns list of Friend', () async {
    when(mockDio.get<List<dynamic>>('/friends')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/friends'),
        data: [
          {
            'user_id': 'u2',
            'display_name': 'Bình',
            'avatar_url': null,
          }
        ],
        statusCode: 200,
      ),
    );

    final friends = await service.getFriends();

    expect(friends, hasLength(1));
    expect(friends.first, isA<Friend>());
    expect(friends.first.displayName, 'Bình');
  });

  test('generateQrOtp returns otp string', () async {
    when(mockDio.post<Map<String, dynamic>>('/friends/qr/generate'))
        .thenAnswer(
      (_) async => Response(
        requestOptions:
            RequestOptions(path: '/friends/qr/generate'),
        data: {'otp': 'abc123'},
        statusCode: 200,
      ),
    );

    final otp = await service.generateQrOtp();
    expect(otp, 'abc123');
  });

  test('removeFriend calls DELETE endpoint', () async {
    when(mockDio.delete<void>('/friends/u2')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/friends/u2'),
        statusCode: 204,
      ),
    );

    await service.removeFriend('u2');
    verify(mockDio.delete<void>('/friends/u2')).called(1);
  });
}
