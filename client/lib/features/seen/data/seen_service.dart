import 'package:dio/dio.dart';

/// HTTP service for marking posts as seen.
class SeenService {
  SeenService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// POST /posts/:postId/seen
  Future<void> markSeen(String postId) async {
    await _dio.post<void>('/posts/$postId/seen');
  }

  /// GET /posts/:postId/seen-by
  ///
  /// Returns a list of display names who have seen the post.
  Future<List<String>> getSeenBy(String postId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/posts/$postId/seen-by',
    );
    final viewers =
        (response.data?['viewers'] as List<dynamic>?) ?? [];
    return viewers
        .cast<Map<String, dynamic>>()
        .map((v) => v['display_name'] as String? ?? '')
        .where((name) => name.isNotEmpty)
        .toList();
  }
}
