import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';

/// Compresses an image file to stay within [maxBytes].
///
/// Uses [XFile] so it works on both mobile and web
/// (no `dart:io` dependency).
class ImageCompressor {
  const ImageCompressor({this.maxBytes = 1024 * 1024}); // 1 MB default

  final int maxBytes;

  /// Reads [file] and returns bytes.
  ///
  /// In production, add `flutter_image_compress` here.
  Future<Uint8List> compress(XFile file) async {
    return file.readAsBytes();
  }
}
