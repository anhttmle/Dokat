import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';

/// Global [Dio] provider — single instance for the entire app.
final dioProvider = Provider<Dio>((ref) => createApiClient());

/// Exposes [FirebaseAuth.instance] for easy mocking in tests.
final firebaseAuthProvider = Provider<FirebaseAuth>(
  (_) => FirebaseAuth.instance,
);
