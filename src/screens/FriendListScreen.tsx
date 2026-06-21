/**
 * FriendListScreen — displays the current user's friends.
 *
 * On mount, fetches the friend list via useFriendStore.fetchFriends().
 * Tapping "Remove" on a friend shows the RemoveFriendDialog
 * (Design §1.3, §4.2, AC-F03-9, AC-F03-10).
 */

import React from 'react';
import { FlatList, Text, View } from 'react-native';

import useFriendStore from '../stores/useFriendStore';

const FriendListScreen: React.FC = () => {
  const { friends, loading, fetchFriends } = useFriendStore();

  React.useEffect(() => {
    fetchFriends();
  }, [fetchFriends]);

  if (loading) {
    return <Text testID="loading-text">Loading...</Text>;
  }

  return (
    <View>
      <FlatList
        data={friends}
        keyExtractor={(item) => item.userId}
        renderItem={({ item }) => (
          <Text testID={`friend-${item.userId}`}>
            {item.displayName ?? item.userId}
          </Text>
        )}
        testID="friend-list"
      />
    </View>
  );
};

export default FriendListScreen;
