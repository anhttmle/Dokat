import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:cross_file/cross_file.dart';

import 'package:dokat/features/capture/data/capture_service.dart';
import 'package:dokat/features/capture/data/image_compressor.dart';

import 'capture_service_test.mocks.dart';

class _FixedCompressor extends ImageCompressor {
  const _FixedCompressor(this.bytes);

  final Uint8List bytes;

  @override
  Future<Uint8List> compress(XFile file) async => bytes;
}

@GenerateMocks([Dio])
void main() {
  late MockDio mockUploadDio;
  late CaptureService service;

  setUp(() {
    mockUploadDio = MockDio();
    service = CaptureService(
      compressor: _FixedCompressor(Uint8List.fromList([1, 2, 3])),
      uploadDio: mockUploadDio,
    );
  });

  test('uploadImage PUTs raw bytes without Authorization header', () async {
    when(
      mockUploadDio.put<void>(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: 'http://localhost:9000/upload'),
        statusCode: 200,
      ),
    );

    await service.uploadImage(
      XFile.fromData(Uint8List(0), mimeType: 'image/jpeg'),
      'http://localhost:9000/pawsnap/posts/u/1.jpg?sig=x',
    );

    final captured = verify(
      mockUploadDio.put<void>(
        'http://localhost:9000/pawsnap/posts/u/1.jpg?sig=x',
        data: captureAnyNamed('data'),
        options: captureAnyNamed('options'),
      ),
    ).captured;

    expect(captured[0], isA<Uint8List>());
    final options = captured[1] as Options;
    expect(options.headers?['Authorization'], isNull);
    expect(options.headers?['Content-Type'], 'image/jpeg');
  });

  test('uploadImage throws when S3 returns non-2xx', () async {
    when(
      mockUploadDio.put<void>(
        any,
        data: anyNamed('data'),
        options: anyNamed('options'),
      ),
    ).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: 'http://localhost:9000/upload'),
        statusCode: 403,
      ),
    );

    expect(
      () => service.uploadImage(
        XFile.fromData(Uint8List(0), mimeType: 'image/jpeg'),
        'http://localhost:9000/upload',
      ),
      throwsA(isA<DioException>()),
    );
  });
}
