import 'package:dio/dio.dart';

import '../domain/pet_profile.dart';

/// HTTP service for pet profile endpoints.
class PetService {
  PetService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /pets
  Future<List<PetProfile>> getPets() async {
    final response = await _dio.get<Map<String, dynamic>>('/pets');
    final list =
        (response.data?['pets'] as List<dynamic>?) ?? [];
    return list
        .cast<Map<String, dynamic>>()
        .map(PetProfile.fromJson)
        .toList();
  }

  /// POST /pets
  Future<PetProfile> createPet(Map<String, dynamic> data) async {
    final response =
        await _dio.post<Map<String, dynamic>>('/pets', data: data);
    return PetProfile.fromJson(response.data!);
  }

  /// GET /pets/:petId
  Future<PetProfile> getPet(String petId) async {
    final response =
        await _dio.get<Map<String, dynamic>>('/pets/$petId');
    return PetProfile.fromJson(response.data!);
  }

  /// PATCH /pets/:petId
  Future<PetProfile> updatePet(
    String petId,
    Map<String, dynamic> fields,
  ) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/pets/$petId',
      data: fields,
    );
    return PetProfile.fromJson(response.data!);
  }

  /// POST /pets/avatar/upload-url
  Future<String> getPetAvatarUploadUrl(String contentType) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/pets/avatar/upload-url',
      data: {'content_type': contentType},
    );
    return response.data!['upload_url'] as String;
  }

  /// PATCH /pets/:petId/link-photo
  ///
  /// [photoId] is the UUID of the post photo to link.
  Future<void> linkPhoto(String petId, String photoId) async {
    await _dio.patch<void>(
      '/pets/$petId/link-photo',
      data: {'photo_id': photoId},
    );
  }

  /// GET /pets/:petId/photos
  ///
  /// Returns a list of CDN URLs for the pet's timeline photos.
  Future<List<String>> getPetPhotos(String petId) async {
    final response =
        await _dio.get<Map<String, dynamic>>('/pets/$petId/photos');
    final photos =
        (response.data?['photos'] as List<dynamic>?) ?? [];
    return photos
        .cast<Map<String, dynamic>>()
        .map((item) => item['cdn_url'] as String)
        .toList();
  }
}
