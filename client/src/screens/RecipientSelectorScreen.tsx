/**
 * RecipientSelectorScreen — choose recipients and send a captured photo.
 *
 * On mount it loads the user's friends and pre-selects all of them
 * (FR-2, AC-F05-1). Each friend can be toggled (FR-3); the "Gửi" button
 * is always enabled, including with 0 recipients (FR-4, AC-F05-4). On
 * send it calls SendService.send; after success it shows "Đã gửi" and
 * removes the send affordance so the same photo cannot be resent
 * (one-shot — FR-10, FR-12, AC-F05-5).
 *
 * Refs: Design §1.1–§1.3, §4.2; FR-1, FR-2, FR-3, FR-4, FR-10, FR-12;
 *       AC-F05-1, AC-F05-3, AC-F05-4, AC-F05-5
 */

import React from 'react';
import {
  FlatList,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import type { CapturedPhoto } from '../services/capture/CaptureService';
import SocialService, { FriendItem } from '../services/SocialService';
import SendService from '../services/SendService';

export interface RecipientSelectorScreenProps {
  /** The CapturedPhoto handed off from F04 to send. */
  photo: CapturedPhoto;
  /** Called after a successful send (host discards the photo). */
  onSent?: () => void;
}

const RecipientSelectorScreen: React.FC<RecipientSelectorScreenProps> = ({
  photo,
  onSent,
}) => {
  const [friends, setFriends] = React.useState<FriendItem[]>([]);
  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [sent, setSent] = React.useState(false);

  React.useEffect(() => {
    SocialService.getFriends().then((data) => {
      setFriends(data.friends);
      setSelected(new Set(data.friends.map((f) => f.user_id)));
    });
  }, []);

  const toggle = React.useCallback((userId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  }, []);

  const handleSend = React.useCallback(async () => {
    await SendService.send(photo, Array.from(selected));
    setSent(true);
    onSent?.();
  }, [photo, selected, onSent]);

  if (sent) {
    return (
      <View>
        <Text testID="sent-status">Đã gửi</Text>
      </View>
    );
  }

  return (
    <View>
      <FlatList
        data={friends}
        keyExtractor={(item) => item.user_id}
        testID="recipient-list"
        renderItem={({ item }) => (
          <TouchableOpacity
            testID={`recipient-${item.user_id}`}
            accessibilityState={{ selected: selected.has(item.user_id) }}
            onPress={() => toggle(item.user_id)}
          >
            <Text>{item.display_name ?? item.user_id}</Text>
          </TouchableOpacity>
        )}
      />
      <TouchableOpacity testID="send-button" onPress={handleSend}>
        <Text>Gửi</Text>
      </TouchableOpacity>
    </View>
  );
};

export default RecipientSelectorScreen;
