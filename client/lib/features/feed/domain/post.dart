/// A photo post visible on the feed.
class Post {
  const Post({
    required this.postId,
    required this.imageUrl,
    required this.senderDisplayName,
    required this.createdAt,
    this.senderAvatarUrl,
    this.petName,
    this.seenByMe = false,
  });

  final String postId;
  final String imageUrl;
  final String senderDisplayName;
  final String? senderAvatarUrl;
  final String? petName;
  final DateTime createdAt;
  final bool seenByMe;

  factory Post.fromJson(Map<String, dynamic> json) {
    return Post(
      postId: json['post_id'] as String,
      imageUrl: json['cdn_url'] as String,
      senderDisplayName:
          json['sender_display_name'] as String? ?? '',
      senderAvatarUrl: json['sender_avatar_url'] as String?,
      petName: json['pet_name'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      seenByMe: json['seen'] as bool? ?? false,
    );
  }

  Post copyWith({bool? seenByMe}) {
    return Post(
      postId: postId,
      imageUrl: imageUrl,
      senderDisplayName: senderDisplayName,
      senderAvatarUrl: senderAvatarUrl,
      petName: petName,
      createdAt: createdAt,
      seenByMe: seenByMe ?? this.seenByMe,
    );
  }
}
