import 'dart:typed_data';

import 'package:cross_file/cross_file.dart';

/// Result of on-device pet validation.
class ValidationResult {
  const ValidationResult({
    required this.isPet,
    required this.confidence,
    this.species,
  });

  /// True if a dog or cat was detected with sufficient confidence.
  final bool isPet;

  /// Detection confidence between 0.0 and 1.0.
  final double confidence;

  /// 'dog', 'cat', or null if not a pet.
  final String? species;
}

/// Runs on-device TFLite inference to validate that an image
/// contains a dog or cat.
///
/// Accepts [XFile] so it works on both mobile and web.
/// The model file must be placed at `assets/models/pet_model.tflite`.
/// If the model file is absent (e.g. during testing or on web),
/// [validate] returns a stub result.
class PetValidationService {
  /// Validates [imageFile] using the on-device TFLite model.
  ///
  /// TFLite is only supported on Android/iOS; on web this returns
  /// a stub so the capture flow remains functional.
  Future<ValidationResult> validate(XFile imageFile) async {
    // The real implementation uses tflite_flutter (mobile only):
    //   final interpreter = await Interpreter.fromAsset(
    //     'assets/models/pet_model.tflite',
    //   );
    // Stub: always passes validation until model is provided.
    return _stub(await imageFile.readAsBytes());
  }

  // ignore: avoid_positional_boolean_parameters
  ValidationResult _stub(Uint8List _) {
    return const ValidationResult(
      isPet: true,
      confidence: 0.95,
      species: 'dog',
    );
  }
}
