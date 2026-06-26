/**
 * HistoryList — render one history section ("Đã gửi" / "Đã nhận").
 *
 * A presentational component: it receives a section title plus a list of
 * items and renders each photo. In ``mode="sent"`` each item shows the
 * CDN image, "{seen_count}/{recipient_count} đã xem" (FR-3, FR-5) and a
 * relative timestamp (reusing F06's ``formatRelativeTime`` — DL-F06-07).
 * In ``mode="received"`` it shows the sender + pet name and a seen flag
 * (FR-3). An empty list renders the section's own empty label.
 *
 * Refs: Design §4.2; FR-3, FR-5; AC-F08-2, AC-F08-3; DL-F08-05
 */

import React from 'react';
import {
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import type {
  ReceivedHistoryItem,
  SentHistoryItem,
} from '../services/HistoryService';
import { formatRelativeTime } from './relativeTime';

type HistoryMode = 'sent' | 'received';

interface SentProps {
  title: string;
  mode: 'sent';
  items: SentHistoryItem[];
  onOpen?: (item: SentHistoryItem) => void;
}

interface ReceivedProps {
  title: string;
  mode: 'received';
  items: ReceivedHistoryItem[];
  onOpen?: (item: ReceivedHistoryItem) => void;
}

type Props = SentProps | ReceivedProps;

const SentRow: React.FC<{
  item: SentHistoryItem;
  onOpen?: (item: SentHistoryItem) => void;
}> = ({ item, onOpen }) => (
  <TouchableOpacity
    testID={`history-item-${item.post_id}`}
    onPress={() => onOpen?.(item)}
    style={styles.row}
  >
    <Image
      testID={`history-image-${item.post_id}`}
      source={{ uri: item.cdn_url }}
      style={styles.image}
    />
    <Text testID={`history-seen-${item.post_id}`}>
      {`${item.seen_count}/${item.recipient_count} đã xem`}
    </Text>
    <Text testID={`history-time-${item.post_id}`}>
      {formatRelativeTime(item.created_at)}
    </Text>
  </TouchableOpacity>
);

const ReceivedRow: React.FC<{
  item: ReceivedHistoryItem;
  onOpen?: (item: ReceivedHistoryItem) => void;
}> = ({ item, onOpen }) => {
  const senderName = item.sender_display_name ?? 'Người dùng';
  const subtitle = item.pet_name
    ? `${senderName} · ${item.pet_name}`
    : senderName;
  return (
    <TouchableOpacity
      testID={`history-item-${item.post_id}`}
      onPress={() => onOpen?.(item)}
      style={item.seen ? styles.row : styles.rowUnseen}
    >
      <Image
        testID={`history-image-${item.post_id}`}
        source={{ uri: item.cdn_url }}
        style={styles.image}
      />
      <Text testID={`history-sender-${item.post_id}`}>{subtitle}</Text>
      <Text testID={`history-time-${item.post_id}`}>
        {formatRelativeTime(item.created_at)}
      </Text>
    </TouchableOpacity>
  );
};

const HistoryList: React.FC<Props> = (props) => {
  const { title, items, mode } = props;

  return (
    <View testID={`history-section-${mode}`} style={styles.section}>
      <Text testID={`history-title-${mode}`} style={styles.title}>
        {title}
      </Text>
      {items.length === 0 ? (
        <Text testID={`history-empty-${mode}`} style={styles.emptyText}>
          Chưa có ảnh nào
        </Text>
      ) : mode === 'sent' ? (
        props.items.map((item) => (
          <SentRow key={item.post_id} item={item} onOpen={props.onOpen} />
        ))
      ) : (
        props.items.map((item) => (
          <ReceivedRow
            key={item.post_id}
            item={item}
            onOpen={props.onOpen}
          />
        ))
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  section: {
    paddingVertical: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  row: {
    padding: 12,
  },
  rowUnseen: {
    padding: 12,
    borderWidth: 2,
    borderColor: '#ff6b6b',
  },
  image: {
    width: '100%',
    height: 200,
    backgroundColor: '#eee',
  },
  emptyText: {
    color: '#888',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
});

export type { HistoryMode };
export default HistoryList;
