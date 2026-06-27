import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/send/data/send_service.dart';

import 'send_service_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late SendService service;

  setUp(() {
    mockDio = MockDio();
    service = SendService(dio: mockDio);
  });

  test('getUploadUrl returns upload_url from response', () async {
    when(
      mockDio.post<Map<String, dynamic>>(
        '/posts/upload-url',
        data: anyNamed('data'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions:
            RequestOptions(path: '/posts/upload-url'),
        data: {'upload_url': 'https://s3.example.com/upload'},
        statusCode: 200,
      ),
    );

    final url = await service.getUploadUrl('image/jpeg');
    expect(url, 'https://s3.example.com/upload');
  });

  test('sendPost calls POST /posts with required fields', () async {
    when(
      mockDio.post<void>(
        '/posts',
        data: anyNamed('data'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/posts'),
        statusCode: 201,
      ),
    );

    await service.sendPost(
      imageUrl: 'https://cdn.example.com/photo.jpg',
      recipientIds: ['u2', 'u3'],
    );

    verify(
      mockDio.post<void>(
        '/posts',
        data: argThat(
          containsPair('recipient_ids', ['u2', 'u3']),
          named: 'data',
        ),
      ),
    ).called(1);
  });
}
