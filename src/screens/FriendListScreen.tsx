/**
 * FriendListScreen — displays the current user's friends.
 *
 * On mount, calls SocialService.getFriends() directly and keeps
 * result in local state.  Tapping "Xóa bạn" shows
 * RemoveFriendDialog; on confirm, calls SocialService.removeFriend()
 * and applies an optimistic update via useFriendStore.
 *
 * Refs: Design §1.3, §4.2; FR-9, FR-10, FR-11;
 *       AC-F03-9, AC-F03-10
 */

import React from 'react';
import {
  FlatList,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import RemoveFriendDialog from '../components/RemoveFriendDialog';
import SocialService, { FriendItem } from '../services/SocialService';
import useFriendStore from '../stores/useFriendStore';

interface SelectedFriend {
  userId: string;
  displayName: string | null;
}

const FriendListScreen: React.FC = () => {
  const [friends, setFriends] = React.useState<FriendItem[]>([]);
  const [selected, setSelected] =
    React.useState<SelectedFriend | null>(null);

  const removeFriendFromStore = useFriendStore(
    (s) => s.removeFriendLocally,
  );

  React.useEffect(() => {
    SocialService.getFriends().then((data) => {
      setFriends(data.friends);
    });
  }, []);

  const handleConfirmRemove = React.useCallback(async () => {
    if (!selected) return;
    const { userId } = selected;
    setSelected(null);
    setFriends((prev) => prev.filter((f) => f.user_id !== userId));
    removeFriendFromStore(userId);
    await SocialService.removeFriend(userId);
  }, [selected, removeFriendFromStore]);

  return (
    <View>
      <FlatList
        data={friends}
        keyExtractor={(item) => item.user_id}
        renderItem={({ item }) => (
          <View>
            <Text testID={`friend-${item.user_id}`}>
              {item.display_name ?? item.user_id}
            </Text>
            <TouchableOpacity
              testID={`remove-btn-${item.user_id}`}
              onPress={() =>
                setSelected({
                  userId: item.user_id,
                  displayName: item.display_name,
                })
              }
            >
              <Text>Xóa bạn</Text>
            </TouchableOpacity>
          </View>
        )}
        testID="friend-list"
      />

      <RemoveFriendDialog
        visible={selected !== null}
        friendName={selected?.displayName ?? null}
        onConfirm={handleConfirmRemove}
        onCancel={() => setSelected(null)}
      />
    </View>
  );
};

export default FriendListScreen;
