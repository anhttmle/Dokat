/// A photo the current user sent within the last 24 h.
class SentHistoryItem {
  const SentHistoryItem({
    required this.postId,
    required this.cdnUrl,
    required this.createdAt,
    required this.recipientCount,
    required this.seenCount,
  });

  final String postId;
  final String cdnUrl;
  final DateTime createdAt;
  final int recipientCount;
  final int seenCount;

  factory SentHistoryItem.fromJson(Map<String, dynamic> json) {
    return SentHistoryItem(
      postId: json['post_id'] as String,
      cdnUrl: json['cdn_url'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      recipientCount: json['recipient_count'] as int? ?? 0,
      seenCount: json['seen_count'] as int? ?? 0,
    );
  }
}

/// A photo the current user received within the last 24 h.
class ReceivedHistoryItem {
  const ReceivedHistoryItem({
    required this.postId,
    required this.senderId,
    required this.cdnUrl,
    required this.createdAt,
    required this.seen,
    this.senderDisplayName,
    this.senderAvatarUrl,
    this.petName,
  });

  final String postId;
  final String senderId;
  final String? senderDisplayName;
  final String? senderAvatarUrl;
  final String? petName;
  final String cdnUrl;
  final DateTime createdAt;
  final bool seen;

  factory ReceivedHistoryItem.fromJson(Map<String, dynamic> json) {
    return ReceivedHistoryItem(
      postId: json['post_id'] as String,
      senderId: json['sender_id'] as String,
      senderDisplayName: json['sender_display_name'] as String?,
      senderAvatarUrl: json['sender_avatar_url'] as String?,
      petName: json['pet_name'] as String?,
      cdnUrl: json['cdn_url'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      seen: json['seen'] as bool? ?? false,
    );
  }
}
