import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../profile/domain/pet_profile.dart';
import '../../data/pet_validation_service.dart';
import '../widgets/pet_picker_overlay.dart';

/// Camera screen for capturing a pet photo.
///
/// Uses the [camera] package for live preview and capture on all platforms.
/// Runs on-device AI validation before proceeding to recipient selection.
class CameraScreen extends ConsumerStatefulWidget {
  const CameraScreen({super.key});

  @override
  ConsumerState<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends ConsumerState<CameraScreen> {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  bool _initializing = true;
  String? _cameraError;

  bool _validating = false;
  PetProfile? _selectedPet;
  final _validator = PetValidationService();

  @override
  void initState() {
    super.initState();
    unawaited(_initCamera());
  }

  Future<void> _initCamera() async {
    try {
      _cameras = await availableCameras();
      if (_cameras.isEmpty) {
        if (mounted) {
          setState(() {
            _initializing = false;
            _cameraError = 'Không tìm thấy camera trên thiết bị.';
          });
        }
        return;
      }
      final backCamera = _cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back,
        orElse: () => _cameras.first,
      );
      _controller = CameraController(
        backCamera,
        ResolutionPreset.high,
      );
      await _controller!.initialize();
      if (mounted) setState(() => _initializing = false);
    } catch (_) {
      if (mounted) {
        setState(() {
          _initializing = false;
          _cameraError = 'Không thể mở camera. Vui lòng kiểm tra quyền truy cập.';
        });
      }
    }
  }

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
      final bytes = await xFile.readAsBytes();
      if (!mounted) return;
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
    return Scaffold(
      appBar: AppBar(title: const Text('Chụp ảnh')),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_initializing) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_cameraError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            _cameraError!,
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return Stack(
      fit: StackFit.expand,
      children: [
        if (_controller != null) CameraPreview(_controller!),
        Positioned(
          bottom: 100,
          left: 0,
          right: 0,
          child: PetPickerOverlay(
            onPetSelected: (pet) => setState(() => _selectedPet = pet),
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
    );
  }
}
