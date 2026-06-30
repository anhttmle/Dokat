import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../profile/domain/pet_profile.dart';
import '../../data/pet_validation_service.dart';
import '../widgets/pet_picker_overlay.dart';

/// Camera screen for capturing a pet photo.
///
/// On mobile: uses the [camera] package for live preview and capture.
/// On web: uses [ImagePicker] (file picker / device camera via browser).
/// Runs on-device AI validation before proceeding to recipient selection.
class CameraScreen extends ConsumerStatefulWidget {
  const CameraScreen({super.key});

  @override
  ConsumerState<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends ConsumerState<CameraScreen> {
  // Mobile-only fields
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _initializing = !kIsWeb;

  bool _validating = false;
  PetProfile? _selectedPet;
  final _validator = PetValidationService();

  @override
  void initState() {
    super.initState();
    if (!kIsWeb) _initCamera();
  }

  Future<void> _initCamera() async {
    _cameras = await availableCameras();
    if (_cameras.isEmpty) {
      setState(() => _initializing = false);
      return;
    }
    _controller = CameraController(
      _cameras.first,
      ResolutionPreset.high,
    );
    await _controller!.initialize();
    if (mounted) setState(() => _initializing = false);
  }

  /// Web: capture via browser camera or file input.
  Future<void> _pickOnWeb() async {
    final picked = await ImagePicker().pickImage(source: ImageSource.camera);
    if (picked == null || !mounted) return;
    await _validateAndPush(XFile(picked.path, bytes: await picked.readAsBytes()));
  }

  /// Mobile: capture with native camera.
  Future<void> _capture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    setState(() => _validating = true);
    try {
      final xFile = await _controller!.takePicture();
      await _validateAndPush(xFile);
    } finally {
      if (mounted) setState(() => _validating = false);
    }
  }

  Future<void> _validateAndPush(XFile xFile) async {
    setState(() => _validating = true);
    try {
      final result = await _validator.validate(xFile);
      if (!mounted) return;
      if (!result.isPet) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Ảnh phải chứa chó hoặc mèo.')),
        );
        return;
      }
      // Read bytes before navigating so web blob URLs remain valid.
      final bytes = await xFile.readAsBytes();
      unawaited(
        context.push<void>(
          '/send/recipients',
          extra: {
            'image_path': xFile.path,
            'image_bytes': bytes,
            'pet_id': _selectedPet?.petId,
          },
        ),
      );
    } finally {
      if (mounted) setState(() => _validating = false);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) {
      return _WebCaptureView(
        validating: _validating,
        selectedPet: _selectedPet,
        onPetSelected: (pet) => setState(() => _selectedPet = pet),
        onPick: _pickOnWeb,
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Chụp ảnh')),
      body: _initializing
          ? const Center(child: CircularProgressIndicator())
          : Stack(
              fit: StackFit.expand,
              children: [
                if (_controller != null) CameraPreview(_controller!),
                Positioned(
                  bottom: 100,
                  left: 0,
                  right: 0,
                  child: PetPickerOverlay(
                    onPetSelected: (pet) =>
                        setState(() => _selectedPet = pet),
                  ),
                ),
                Positioned(
                  bottom: 24,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: _validating
                        ? const CircularProgressIndicator(color: Colors.white)
                        : GestureDetector(
                            onTap: _capture,
                            child: Container(
                              width: 72,
                              height: 72,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: Colors.white,
                                  width: 4,
                                ),
                              ),
                            ),
                          ),
                  ),
                ),
              ],
            ),
    );
  }
}

/// Web fallback: a simple "pick image" button instead of live camera.
class _WebCaptureView extends StatelessWidget {
  const _WebCaptureView({
    required this.validating,
    required this.selectedPet,
    required this.onPetSelected,
    required this.onPick,
  });

  final bool validating;
  final PetProfile? selectedPet;
  final ValueChanged<PetProfile?> onPetSelected;
  final VoidCallback onPick;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Chụp ảnh')),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            PetPickerOverlay(onPetSelected: onPetSelected),
            const SizedBox(height: 24),
            if (validating)
              const CircularProgressIndicator()
            else
              FilledButton.icon(
                onPressed: onPick,
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Chọn ảnh từ thiết bị'),
              ),
          ],
        ),
      ),
    );
  }
}
