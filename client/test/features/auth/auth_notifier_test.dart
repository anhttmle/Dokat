import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/auth/data/auth_service.dart';
import 'package:dokat/features/auth/domain/auth_state.dart';
import 'package:dokat/features/auth/presentation/providers/auth_notifier.dart';

import 'auth_notifier_test.mocks.dart';

@GenerateMocks([AuthService])
void main() {
  late MockAuthService mockService;

  setUp(() {
    mockService = MockAuthService();
    when(mockService.hasJwtSession()).thenAnswer((_) async => false);
  });

  ProviderContainer makeContainer() {
    final container = ProviderContainer(
      overrides: [
        authNotifierProvider.overrideWith(
          (ref) => AuthNotifier(mockService),
        ),
      ],
    );
    container.read(authNotifierProvider);
    return container;
  }

  test('emits AuthAuthenticated after signInWithDeviceId', () async {
    when(mockService.signInWithDeviceId()).thenAnswer((_) async {});
    when(mockService.getJwtUserId())
        .thenAnswer((_) async => 'user-uuid');

    final container = makeContainer();
    addTearDown(container.dispose);

    await Future<void>.delayed(const Duration(milliseconds: 50));

    final state = container.read(authNotifierProvider);
    expect(state, isA<AuthAuthenticated>());
    expect((state as AuthAuthenticated).userId, 'user-uuid');
  });

  test('reuses existing JWT session without calling signInWithDeviceId',
      () async {
    when(mockService.hasJwtSession()).thenAnswer((_) async => true);
    when(mockService.getJwtUserId())
        .thenAnswer((_) async => 'existing-user');

    final container = makeContainer();
    addTearDown(container.dispose);

    await Future<void>.delayed(const Duration(milliseconds: 50));

    final state = container.read(authNotifierProvider);
    expect(state, isA<AuthAuthenticated>());
    verifyNever(mockService.signInWithDeviceId());
  });

  test('emits AuthError when signInWithDeviceId fails', () async {
    when(mockService.signInWithDeviceId())
        .thenThrow(Exception('network error'));

    final container = makeContainer();
    addTearDown(container.dispose);

    await Future<void>.delayed(const Duration(milliseconds: 50));

    final state = container.read(authNotifierProvider);
    expect(state, isA<AuthError>());
  });
}
