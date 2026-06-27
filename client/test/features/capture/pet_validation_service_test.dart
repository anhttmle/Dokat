import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dokat/features/capture/data/pet_validation_service.dart';

void main() {
  test('stub validate returns isPet=true', () async {
    final service = PetValidationService();
    // Use XFile with in-memory bytes — no dart:io dependency.
    final xFile = XFile.fromData(
      Uint8List.fromList([0xff, 0xd8, 0xff]), // JPEG magic bytes
      mimeType: 'image/jpeg',
      name: 'test_image.jpg',
    );

    final result = await service.validate(xFile);

    expect(result.isPet, isTrue);
    expect(result.confidence, greaterThan(0.5));
  });
}
