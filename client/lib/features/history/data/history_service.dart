import 'package:dio/dio.dart';

import '../../feed/domain/post.dart';

/// HTTP service for the history (sent/received) endpoints.
class HistoryService {
  HistoryService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /history/sent
  Future<List<Post>> getSentHistory() async {
    final response = await _dio.get<List<dynamic>>('/history/sent');
    return (response.data ?? [])
        .cast<Map<String, dynamic>>()
        .map(Post.fromJson)
        .toList();
  }

  /// GET /history/received
  Future<List<Post>> getReceivedHistory() async {
    final response =
        await _dio.get<List<dynamic>>('/history/received');
    return (response.data ?? [])
        .cast<Map<String, dynamic>>()
        .map(Post.fromJson)
        .toList();
  }
}
