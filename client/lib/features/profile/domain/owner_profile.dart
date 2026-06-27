/// Owner (user) profile data.
class OwnerProfile {
  const OwnerProfile({
    required this.userId,
    required this.displayName,
    this.avatarUrl,
    this.bio,
  });

  final String userId;
  final String displayName;
  final String? avatarUrl;
  final String? bio;

  factory OwnerProfile.fromJson(Map<String, dynamic> json) {
    return OwnerProfile(
      userId: json['user_id'] as String,
      displayName: json['display_name'] as String,
      avatarUrl: json['avatar_url'] as String?,
      bio: json['bio'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'display_name': displayName,
        if (bio != null) 'bio': bio,
      };

  OwnerProfile copyWith({
    String? displayName,
    String? avatarUrl,
    String? bio,
  }) {
    return OwnerProfile(
      userId: userId,
      displayName: displayName ?? this.displayName,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      bio: bio ?? this.bio,
    );
  }
}
