import 'package:dio/dio.dart';

import '../domain/owner_profile.dart';

/// HTTP service for owner profile endpoints.
class ProfileService {
  ProfileService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /profile/me
  Future<OwnerProfile> getProfile() async {
    final response = await _dio.get<Map<String, dynamic>>('/profile/me');
    return OwnerProfile.fromJson(response.data!);
  }

  /// PATCH /profile/me
  Future<OwnerProfile> updateProfile(Map<String, dynamic> fields) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/profile/me',
      data: fields,
    );
    return OwnerProfile.fromJson(response.data!);
  }

  /// POST /profile/me/avatar/upload-url
  ///
  /// Returns a presigned S3 upload URL.
  Future<String> getAvatarUploadUrl(String contentType) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/profile/me/avatar/upload-url',
      data: {'content_type': contentType},
    );
    return response.data!['upload_url'] as String;
  }
}
