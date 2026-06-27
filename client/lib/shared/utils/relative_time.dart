/// Formats a [DateTime] as a human-readable relative time string.
///
/// Example: "2 giờ trước", "vừa xong", "3 ngày trước".
String relativeTime(DateTime dateTime) {
  final now = DateTime.now();
  final diff = now.difference(dateTime);

  if (diff.inSeconds < 60) return 'vừa xong';
  if (diff.inMinutes < 60) return '${diff.inMinutes} phút trước';
  if (diff.inHours < 24) return '${diff.inHours} giờ trước';
  if (diff.inDays < 7) return '${diff.inDays} ngày trước';
  return '${(diff.inDays / 7).floor()} tuần trước';
}
