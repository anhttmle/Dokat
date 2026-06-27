import 'package:dio/dio.dart';

import '../domain/history_item.dart';

/// HTTP service for the history (sent/received) endpoints.
class HistoryService {
  HistoryService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /history/sent
  Future<List<SentHistoryItem>> getSentHistory() async {
    final response = await _dio.get<dynamic>('/history/sent');
    final data = response.data as Map<String, dynamic>;
    final items = data['items'] as List<dynamic>? ?? [];
    return items
        .cast<Map<String, dynamic>>()
        .map(SentHistoryItem.fromJson)
        .toList();
  }

  /// GET /history/received
  Future<List<ReceivedHistoryItem>> getReceivedHistory() async {
    final response = await _dio.get<dynamic>('/history/received');
    final data = response.data as Map<String, dynamic>;
    final items = data['items'] as List<dynamic>? ?? [];
    return items
        .cast<Map<String, dynamic>>()
        .map(ReceivedHistoryItem.fromJson)
        .toList();
  }
}
