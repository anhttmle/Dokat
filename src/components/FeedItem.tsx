/**
 * FeedItem — render a single received post on the feed.
 *
 * Shows the CDN image (with a placeholder while loading — FR-8), the
 * sender's display name and pet name (FR-4), a relative timestamp
 * (DL-F06-07) and an "unseen" indicator when the post has not been
 * opened yet (FR-6, AC-F06-3).
 *
 * Refs: Design §4.2; FR-4, FR-6, FR-8; AC-F06-1, AC-F06-3; DL-F06-07
 */

import React from 'react';
import {
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import type { FeedItem as FeedItemData } from '../services/FeedService';
import { formatRelativeTime } from './relativeTime';

interface Props {
  item: FeedItemData;
  onPress?: (item: FeedItemData) => void;
}

const PLACEHOLDER_URI =
  'https://cdn.pawsnap.app/static/feed-placeholder.png';

const FeedItem: React.FC<Props> = ({ item, onPress }) => {
  const senderName = item.sender_display_name ?? 'Người dùng';
  const subtitle = item.pet_name
    ? `${senderName} · ${item.pet_name}`
    : senderName;

  return (
    <TouchableOpacity
      testID={`feed-item-${item.post_id}`}
      onPress={() => onPress?.(item)}
      style={item.seen ? styles.container : styles.containerUnseen}
    >
      <Image
        testID={`feed-image-${item.post_id}`}
        source={{ uri: item.cdn_url }}
        defaultSource={{ uri: PLACEHOLDER_URI }}
        style={styles.image}
      />
      {!item.seen && (
        <View
          testID={`unseen-indicator-${item.post_id}`}
          style={styles.unseenDot}
        />
      )}
      <Text testID={`feed-sender-${item.post_id}`}>{subtitle}</Text>
      <Text testID={`feed-time-${item.post_id}`}>
        {formatRelativeTime(item.created_at)}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 12,
  },
  containerUnseen: {
    padding: 12,
    borderWidth: 2,
    borderColor: '#ff6b6b',
  },
  image: {
    width: '100%',
    height: 240,
    backgroundColor: '#eee',
  },
  unseenDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#ff6b6b',
  },
});

export default FeedItem;
