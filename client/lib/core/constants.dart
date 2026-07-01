/// App-wide constants.
class Constants {
  Constants._();

  /// Base URL for the FastAPI backend (compile-time override).
  ///
  /// Prefer [resolveApiBaseUrl] in [api_config.dart] — it picks the correct
  /// URL per platform (web Docker proxy, local dev, dart-define).
  static const String baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: '',
  );

  /// Maximum number of friends a user can have.
  static const int maxFriends = 20;

  /// Free-tier pet profile limit (matches backend FREE_USER_PET_LIMIT).
  static const int maxPetsFree = 1;

  /// Number of days before a guest account must link OAuth.
  static const int guestLinkDeadlineDays = 7;

  /// Post visibility window in hours.
  static const int postVisibilityHours = 24;
}
