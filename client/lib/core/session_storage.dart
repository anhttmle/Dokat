import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Platform-agnostic key-value storage for auth session data.
///
/// Web: uses [SharedPreferences] (localStorage) — does not require
/// the Web Crypto API, so it works over plain HTTP on LAN.
/// Mobile/desktop: uses [FlutterSecureStorage] (OS keychain / keystore).
abstract class SessionStorage {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
}

/// Creates the appropriate [SessionStorage] for the current platform.
///
/// Must be called after [WidgetsFlutterBinding.ensureInitialized].
Future<SessionStorage> createSessionStorage() async {
  if (kIsWeb) {
    return _SharedPreferencesStorage(
      await SharedPreferences.getInstance(),
    );
  }
  return _SecureStorage(const FlutterSecureStorage());
}

class _SecureStorage implements SessionStorage {
  const _SecureStorage(this._storage);

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);
}

class _SharedPreferencesStorage implements SessionStorage {
  const _SharedPreferencesStorage(this._prefs);

  final SharedPreferences _prefs;

  @override
  Future<String?> read(String key) async => _prefs.getString(key);

  @override
  Future<void> write(String key, String value) async =>
      _prefs.setString(key, value);

  @override
  Future<void> delete(String key) async => _prefs.remove(key);
}
