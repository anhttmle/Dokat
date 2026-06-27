import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/auth/data/auth_service.dart';
import 'package:dokat/features/auth/domain/auth_state.dart';
import 'package:dokat/features/auth/presentation/providers/auth_notifier.dart';

import 'auth_notifier_test.mocks.dart';

@GenerateMocks([AuthService, User])
void main() {
  late MockAuthService mockService;
  late StreamController<User?> userController;

  setUp(() {
    mockService = MockAuthService();
    userController = StreamController<User?>.broadcast();
    when(mockService.userChanges).thenAnswer((_) => userController.stream);
  });

  tearDown(() => userController.close());

  /// Creates a container and immediately triggers [AuthNotifier] creation
  /// so the stream subscription is registered before we emit events.
  ProviderContainer makeContainer() {
    final container = ProviderContainer(
      overrides: [
        authNotifierProvider.overrideWith(
          (ref) => AuthNotifier(mockService),
        ),
      ],
    );
    // Trigger lazy creation so the stream subscription is active.
    container.read(authNotifierProvider);
    return container;
  }

  test('emits AuthAuthenticated with isGuest=true for linked=false user',
      () async {
    final mockUser = MockUser();
    when(mockService.isLinked).thenReturn(false);
    when(mockService.creationTime)
        .thenReturn(DateTime.now().subtract(const Duration(days: 1)));

    final container = makeContainer();
    addTearDown(container.dispose);

    userController.add(mockUser);
    await Future<void>.delayed(const Duration(milliseconds: 50));

    final state = container.read(authNotifierProvider);
    expect(state, isA<AuthAuthenticated>());
    expect((state as AuthAuthenticated).isGuest, isTrue);
  });

  test('emits AuthForceLinkRequired after 7 days guest', () async {
    final mockUser = MockUser();
    when(mockService.isLinked).thenReturn(false);
    when(mockService.creationTime)
        .thenReturn(DateTime.now().subtract(const Duration(days: 8)));

    final container = makeContainer();
    addTearDown(container.dispose);

    userController.add(mockUser);
    await Future<void>.delayed(const Duration(milliseconds: 50));

    final state = container.read(authNotifierProvider);
    expect(state, isA<AuthForceLinkRequired>());
  });

  test('emits AuthAuthenticated with isGuest=false when linked', () async {
    final mockUser = MockUser();
    when(mockService.isLinked).thenReturn(true);
    when(mockService.creationTime).thenReturn(DateTime.now());

    final container = makeContainer();
    addTearDown(container.dispose);

    userController.add(mockUser);
    await Future<void>.delayed(const Duration(milliseconds: 50));

    final state = container.read(authNotifierProvider);
    expect(state, isA<AuthAuthenticated>());
    expect((state as AuthAuthenticated).isGuest, isFalse);
  });

  test('calls signInAnonymously when user stream emits null', () async {
    when(mockService.signInAnonymously())
        .thenAnswer((_) async => throw UnimplementedError());

    final container = makeContainer();
    addTearDown(container.dispose);

    userController.add(null);
    await Future<void>.delayed(const Duration(milliseconds: 50));

    verify(mockService.signInAnonymously()).called(1);
  });
}
