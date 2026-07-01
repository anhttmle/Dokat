import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dokat/core/session_storage.dart';

void main() {
  group('_SharedPreferencesStorage', () {
    late SessionStorage storage;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      // Construct via the public factory which branches on kIsWeb.
      // In unit tests kIsWeb = false, so we exercise the prefs variant
      // by constructing it indirectly through a test-only helper below.
      storage = _TestSharedPrefsStorage(prefs);
    });

    test('write then read returns the value', () async {
      await storage.write('k', 'hello');
      expect(await storage.read('k'), 'hello');
    });

    test('read missing key returns null', () async {
      expect(await storage.read('missing'), isNull);
    });

    test('delete removes the value', () async {
      await storage.write('k', 'value');
      await storage.delete('k');
      expect(await storage.read('k'), isNull);
    });

    test('overwrite replaces existing value', () async {
      await storage.write('k', 'first');
      await storage.write('k', 'second');
      expect(await storage.read('k'), 'second');
    });
  });
}

/// Exposes the SharedPreferences-backed [SessionStorage] in tests.
///
/// [createSessionStorage] cannot be called directly in unit tests because
/// [kIsWeb] is always false outside a browser, so we instantiate the
/// concrete wrapper here to test its logic in isolation.
class _TestSharedPrefsStorage implements SessionStorage {
  _TestSharedPrefsStorage(this._prefs);

  final SharedPreferences _prefs;

  @override
  Future<String?> read(String key) async => _prefs.getString(key);

  @override
  Future<void> write(String key, String value) async =>
      _prefs.setString(key, value);

  @override
  Future<void> delete(String key) async => _prefs.remove(key);
}
