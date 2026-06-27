import 'package:dio/dio.dart';

/// HTTP service for sending photo posts to recipients.
class SendService {
  SendService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// POST /posts/upload-url
  ///
  /// Returns a presigned S3 URL for uploading the image.
  Future<String> getUploadUrl(String contentType) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/posts/upload-url',
      data: {'content_type': contentType},
    );
    return response.data!['upload_url'] as String;
  }

  /// POST /posts
  ///
  /// Creates a post record linking [imageUrl] to [recipientIds].
  /// Optionally includes [petId] and [locationPayload].
  Future<void> sendPost({
    required String imageUrl,
    required List<String> recipientIds,
    String? petId,
    Map<String, dynamic>? locationPayload,
  }) async {
    await _dio.post<void>(
      '/posts',
      data: {
        'image_url': imageUrl,
        'recipient_ids': recipientIds,
        if (petId != null) 'pet_id': petId,
        if (locationPayload != null) 'location': locationPayload,
      },
    );
  }
}
