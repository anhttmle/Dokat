import 'package:dio/dio.dart';

/// HTTP service for sending photo posts to recipients.
class SendService {
  SendService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// POST /posts/upload-url
  ///
  /// Returns a record with the presigned S3 upload URL, the S3 object
  /// key, and the public CDN URL — all needed for the subsequent
  /// POST /posts call.
  Future<({String uploadUrl, String s3Key, String cdnUrl})>
      getUploadUrl(String contentType) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/posts/upload-url',
      data: {'content_type': contentType},
    );
    final data = response.data!;
    return (
      uploadUrl: data['upload_url'] as String,
      s3Key: data['object_key'] as String,
      cdnUrl: data['cdn_url'] as String,
    );
  }

  /// POST /posts
  ///
  /// Creates a post record linking [s3Key] + [cdnUrl] to [recipientIds].
  /// Optionally includes [petId], [latitude], and [longitude].
  Future<void> sendPost({
    required String s3Key,
    required String cdnUrl,
    required List<String> recipientIds,
    String? petId,
    double? latitude,
    double? longitude,
  }) async {
    await _dio.post<void>(
      '/posts',
      data: {
        's3_key': s3Key,
        'cdn_url': cdnUrl,
        'recipient_ids': recipientIds,
        if (petId != null) 'pet_id': petId,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
      },
    );
  }
}
