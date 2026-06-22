/**
 * FeedScreen — the main screen after login: the received-photo feed.
 *
 * On mount it loads the feed via FeedService.getFeed() (FR-1) and renders
 * a FlatList preserving the server order (FR-2). Pull-to-refresh reloads
 * the feed (FR-7). When the feed is empty it shows an empty state with a
 * prompt to add friends (FR-9). Tapping an item opens it full-screen,
 * optimistically marks it as seen and calls FeedService.markSeen() — the
 * F07 integration point (FR-5, DL-F06-02).
 *
 * Refs: Design §1.1, §1.2, §1.4, §1.5, §4.2; FR-1, FR-2, FR-5, FR-7,
 *       FR-9; AC-F06-3, AC-F06-4, AC-F06-5, AC-F06-6; DL-F06-02
 */

import React from 'react';
import { FlatList, RefreshControl, Text, View } from 'react-native';

import FeedItemRow from '../components/FeedItem';
import FeedService, { FeedItem } from '../services/FeedService';

const FeedScreen: React.FC = () => {
  const [items, setItems] = React.useState<FeedItem[]>([]);
  const [refreshing, setRefreshing] = React.useState(false);

  const loadFeed = React.useCallback(async () => {
    const result = await FeedService.getFeed();
    setItems(result.items);
  }, []);

  React.useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  const handleRefresh = React.useCallback(async () => {
    setRefreshing(true);
    try {
      await loadFeed();
    } finally {
      setRefreshing(false);
    }
  }, [loadFeed]);

  const handleOpen = React.useCallback((opened: FeedItem) => {
    setItems((prev) =>
      prev.map((it) =>
        it.post_id === opened.post_id ? { ...it, seen: true } : it,
      ),
    );
    FeedService.markSeen(opened.post_id);
  }, []);

  if (items.length === 0) {
    return (
      <View testID="feed-empty-state">
        <Text>Thêm bạn bè để xem ảnh thú cưng của họ</Text>
      </View>
    );
  }

  return (
    <FlatList
      testID="feed-list"
      data={items}
      keyExtractor={(item) => item.post_id}
      renderItem={({ item }) => (
        <FeedItemRow item={item} onPress={handleOpen} />
      )}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
        />
      }
    />
  );
};

export default FeedScreen;
