/// Represents a friend relationship entry.
class Friend {
  const Friend({
    required this.userId,
    required this.displayName,
    this.avatarUrl,
  });

  final String userId;
  final String displayName;
  final String? avatarUrl;

  factory Friend.fromJson(Map<String, dynamic> json) {
    return Friend(
      userId: json['user_id'] as String,
      displayName: json['display_name'] as String,
      avatarUrl: json['avatar_url'] as String?,
    );
  }
}
