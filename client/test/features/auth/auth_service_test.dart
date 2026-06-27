import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';

import 'package:dokat/features/auth/data/auth_service.dart';

import 'auth_service_test.mocks.dart';

@GenerateMocks([FirebaseAuth, User, UserCredential])
void main() {
  late MockFirebaseAuth mockAuth;
  late MockUser mockUser;
  late AuthService service;

  setUp(() {
    mockAuth = MockFirebaseAuth();
    mockUser = MockUser();
    service = AuthService(auth: mockAuth);
  });

  group('AuthService.isLinked', () {
    test('returns false when user has only firebase provider', () {
      final mockInfo = _MockProviderInfo('firebase');
      when(mockAuth.currentUser).thenReturn(mockUser);
      when(mockUser.providerData).thenReturn([mockInfo]);

      expect(service.isLinked, isFalse);
    });

    test('returns true when user has google provider', () {
      final mockInfo = _MockProviderInfo('google.com');
      when(mockAuth.currentUser).thenReturn(mockUser);
      when(mockUser.providerData).thenReturn([mockInfo]);

      expect(service.isLinked, isTrue);
    });
  });

  group('AuthService.signInAnonymously', () {
    test('delegates to FirebaseAuth', () async {
      final mockCred = MockUserCredential();
      when(mockAuth.signInAnonymously())
          .thenAnswer((_) async => mockCred);

      final result = await service.signInAnonymously();

      verify(mockAuth.signInAnonymously()).called(1);
      expect(result, mockCred);
    });
  });
}

class _MockProviderInfo extends Fake implements UserInfo {
  _MockProviderInfo(this._providerId);
  final String _providerId;

  @override
  String get providerId => _providerId;
}
