import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';
import 'package:dio/dio.dart';

import 'image_compressor.dart';

/// Handles image upload to S3 via presigned URL.
///
/// Uses [XFile] instead of `dart:io.File` so it works on web.
/// The upload URL is obtained from [SendService] (POST /posts/upload-url).
class CaptureService {
  CaptureService({
    required Dio dio,
    ImageCompressor? compressor,
  })  : _dio = dio,
        _compressor = compressor ?? const ImageCompressor();

  final Dio _dio;
  final ImageCompressor _compressor;

  /// Compresses [imageFile] and uploads it to [uploadUrl] (S3 presigned).
  Future<void> uploadImage(XFile imageFile, String uploadUrl) async {
    final bytes = await _compressor.compress(imageFile);
    await _uploadToS3(uploadUrl, bytes);
  }

  Future<void> _uploadToS3(String url, Uint8List bytes) async {
    await _dio.put<void>(
      url,
      data: Stream.fromIterable(bytes.map((b) => [b])),
      options: Options(
        headers: {
          'Content-Type': 'image/jpeg',
          'Content-Length': bytes.length,
        },
      ),
    );
  }
}
