import 'package:dio/dio.dart';

import '../domain/pet_profile.dart';

/// HTTP service for pet profile endpoints.
class PetService {
  PetService({required Dio dio}) : _dio = dio;

  final Dio _dio;

  /// GET /pets
  Future<List<PetProfile>> getPets() async {
    final response = await _dio.get<List<dynamic>>('/pets');
    return (response.data ?? [])
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
  Future<void> linkPhoto(String petId, String photoUrl) async {
    await _dio.patch<void>(
      '/pets/$petId/link-photo',
      data: {'photo_url': photoUrl},
    );
  }

  /// GET /pets/:petId/photos
  Future<List<String>> getPetPhotos(String petId) async {
    final response =
        await _dio.get<List<dynamic>>('/pets/$petId/photos');
    return (response.data ?? []).cast<String>();
  }
}
