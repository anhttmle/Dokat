import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/feed/data/feed_service.dart';
import 'package:dokat/features/feed/domain/post.dart';

import 'feed_service_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  late MockDio mockDio;
  late FeedService service;

  setUp(() {
    mockDio = MockDio();
    service = FeedService(dio: mockDio);
  });

  test('getFeed parses list of Post', () async {
    when(mockDio.get<dynamic>('/feed')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/feed'),
        data: {
          'items': [
          {
            'post_id': 'p1',
            'cdn_url': 'https://cdn.example.com/p1.jpg',
            'sender_display_name': 'Anh',
            'sender_avatar_url': null,
            'pet_name': 'Mochi',
            'created_at': '2026-06-26T10:00:00Z',
            'seen': false,
          }
        ]},
        statusCode: 200,
      ),
    );

    final posts = await service.getFeed();

    expect(posts, hasLength(1));
    expect(posts.first, isA<Post>());
    expect(posts.first.postId, 'p1');
    expect(posts.first.petName, 'Mochi');
  });
}
