/**
 * SeenByList — render "N người đã xem" plus the list of viewers.
 *
 * A pure presentational component: it receives a ``SeenByResult`` and
 * renders the aggregate count (FR-4) followed by each viewer's display
 * name and avatar (FR-3). An empty viewer list shows an empty state.
 * F08 owns fetching (``SeenService.getSeenBy``) and mounting this into
 * the History screen (DL-F07-06).
 *
 * Refs: Design §4.2; FR-3, FR-4; AC-F07-2; DL-F07-06
 */

import React from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';

import type { SeenByResult, SeenViewer } from '../services/SeenService';

interface Props {
  result: SeenByResult;
}

const SeenByList: React.FC<Props> = ({ result }) => {
  const { seen_count, viewers } = result;

  if (viewers.length === 0) {
    return (
      <View testID="seen-by-empty" style={styles.container}>
        <Text style={styles.emptyText}>Chưa có ai xem</Text>
      </View>
    );
  }

  return (
    <View testID="seen-by-list" style={styles.container}>
      <Text testID="seen-by-count" style={styles.countText}>
        {`${seen_count} người đã xem`}
      </Text>
      {viewers.map((viewer: SeenViewer) => (
        <View
          key={viewer.user_id}
          testID={`seen-by-viewer-${viewer.user_id}`}
          style={styles.viewerRow}
        >
          {viewer.avatar_url ? (
            <Image
              testID={`seen-by-avatar-${viewer.user_id}`}
              source={{ uri: viewer.avatar_url }}
              style={styles.avatar}
            />
          ) : null}
          <Text style={styles.viewerName}>
            {viewer.display_name ?? 'Người dùng'}
          </Text>
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
  },
  countText: {
    fontWeight: '600',
    marginBottom: 8,
  },
  emptyText: {
    color: '#888',
  },
  viewerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    marginRight: 8,
    backgroundColor: '#eee',
  },
  viewerName: {
    fontSize: 15,
  },
});

export default SeenByList;
