import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/profile/data/profile_service.dart';
import 'package:dokat/features/profile/domain/owner_profile.dart';

import 'profile_service_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late ProfileService service;

  setUp(() {
    mockDio = MockDio();
    service = ProfileService(dio: mockDio);
  });

  test('getProfile parses OwnerProfile from JSON', () async {
    when(mockDio.get<Map<String, dynamic>>('/profile/me')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/profile/me'),
        data: {
          'user_id': 'u1',
          'display_name': 'Anh',
          'avatar_url': null,
          'bio': null,
        },
        statusCode: 200,
      ),
    );

    final profile = await service.getProfile();

    expect(profile, isA<OwnerProfile>());
    expect(profile.displayName, 'Anh');
  });

  test('updateProfile sends PATCH and returns updated profile', () async {
    when(
      mockDio.patch<Map<String, dynamic>>(
        '/profile/me',
        data: anyNamed('data'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/profile/me'),
        data: {
          'user_id': 'u1',
          'display_name': 'New Name',
          'avatar_url': null,
          'bio': 'Hello',
        },
        statusCode: 200,
      ),
    );

    final profile =
        await service.updateProfile({'display_name': 'New Name'});

    expect(profile.displayName, 'New Name');
  });
}
