import 'package:dio/dio.dart';

import '../domain/post.dart';

/// HTTP service for the feed endpoint.
class FeedService {
  FeedService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /feed
  Future<List<Post>> getFeed() async {
    final response = await _dio.get<dynamic>('/feed');
    final raw = response.data;
    final items = raw is Map
        ? (raw['items'] as List<dynamic>? ?? [])
        : (raw as List<dynamic>? ?? []);
    return items
        .cast<Map<String, dynamic>>()
        .map(Post.fromJson)
        .toList();
  }
}
