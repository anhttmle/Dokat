/// App-wide constants.
class Constants {
  Constants._();

  /// Base URL for the FastAPI backend.
  /// Override via --dart-define=BASE_URL=https://... for prod.
  static const String baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// Maximum number of friends a user can have.
  static const int maxFriends = 20;

  /// Number of days before a guest account must link OAuth.
  static const int guestLinkDeadlineDays = 7;

  /// Post visibility window in hours.
  static const int postVisibilityHours = 24;
}
