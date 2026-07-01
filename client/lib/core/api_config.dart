import 'package:flutter/foundation.dart' show kIsWeb;

/// Resolves the FastAPI base URL for the current platform and deployment.
///
/// * **Docker web** (nginx `/api` proxy): uses `{page-origin}/api` at runtime
///   so the same build works from localhost, LAN IP, or public DNS.
/// * **Local `flutter run`**: defaults to `http://localhost:8000`.
/// * **Override**: `--dart-define=BASE_URL=https://api.example.com`
String resolveApiBaseUrl() {
  const envUrl = String.fromEnvironment('BASE_URL');
  if (envUrl.isNotEmpty) {
    return envUrl;
  }
  if (kIsWeb) {
    return '${Uri.base.origin}/api';
  }
  return 'http://localhost:8000';
}
