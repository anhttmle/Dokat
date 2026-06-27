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

  test('getUploadUrl returns upload_url, s3Key, cdnUrl', () async {
    when(
      mockDio.post<Map<String, dynamic>>(
        '/posts/upload-url',
        data: anyNamed('data'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions:
            RequestOptions(path: '/posts/upload-url'),
        data: {
          'upload_url': 'https://s3.example.com/upload?sig=x',
          'object_key': 'posts/abc123.jpg',
          'cdn_url': 'https://cdn.example.com/posts/abc123.jpg',
          'expires_in': 300,
        },
        statusCode: 200,
      ),
    );

    final result = await service.getUploadUrl('image/jpeg');
    expect(
      result.uploadUrl,
      'https://s3.example.com/upload?sig=x',
    );
    expect(result.s3Key, 'posts/abc123.jpg');
    expect(
      result.cdnUrl,
      'https://cdn.example.com/posts/abc123.jpg',
    );
  });

  test('sendPost calls POST /posts with s3_key and cdn_url', () async {
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
      s3Key: 'posts/abc123.jpg',
      cdnUrl: 'https://cdn.example.com/posts/abc123.jpg',
      recipientIds: ['u2', 'u3'],
    );

    verify(
      mockDio.post<void>(
        '/posts',
        data: argThat(
          allOf(
            containsPair('s3_key', 'posts/abc123.jpg'),
            containsPair('recipient_ids', ['u2', 'u3']),
          ),
          named: 'data',
        ),
      ),
    ).called(1);
  });
}
