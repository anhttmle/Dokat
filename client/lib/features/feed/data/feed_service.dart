import 'package:dio/dio.dart';

import '../domain/post.dart';

/// HTTP service for the feed endpoint.
class FeedService {
  FeedService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /feed
  Future<List<Post>> getFeed() async {
    final response = await _dio.get<List<dynamic>>('/feed');
    return (response.data ?? [])
        .cast<Map<String, dynamic>>()
        .map(Post.fromJson)
        .toList();
  }
}
