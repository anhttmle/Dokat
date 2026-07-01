import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';
import 'package:dio/dio.dart';

import 'image_compressor.dart';

/// Handles image upload to S3 via presigned URL.
///
/// Uses [XFile] instead of `dart:io.File` so it works on web.
/// The upload URL is obtained from [SendService] (POST /posts/upload-url).
///
/// S3 PUT uses a separate [Dio] without auth interceptors — presigned URLs
/// reject extra headers such as `Authorization`.
class CaptureService {
  CaptureService({
    ImageCompressor? compressor,
    Dio? uploadDio,
  })  : _compressor = compressor ?? const ImageCompressor(),
        _uploadDio = uploadDio ??
            Dio(
              BaseOptions(
                connectTimeout: const Duration(seconds: 30),
                receiveTimeout: const Duration(seconds: 60),
              ),
            );

  final ImageCompressor _compressor;
  final Dio _uploadDio;

  /// Compresses [imageFile] and uploads it to [uploadUrl] (S3 presigned).
  Future<void> uploadImage(XFile imageFile, String uploadUrl) async {
    final bytes = await _compressor.compress(imageFile);
    await _uploadToS3(uploadUrl, bytes);
  }

  Future<void> _uploadToS3(String url, Uint8List bytes) async {
    final response = await _uploadDio.put<void>(
      url,
      data: bytes,
      options: Options(
        headers: {
          'Content-Type': 'image/jpeg',
          'Content-Length': bytes.length,
        },
      ),
    );
    final status = response.statusCode;
    if (status == null || status < 200 || status >= 300) {
      throw DioException(
        requestOptions: response.requestOptions,
        response: response,
        message: 'S3 upload failed: HTTP $status',
      );
    }
  }
}
