/**
 * RemoveFriendDialog — confirmation modal before removing a friend.
 *
 * Shows the friend's name and two buttons: Confirm and Cancel.
 * The parent is responsible for calling SocialService.removeFriend()
 * after confirmation (Design §1.3, §4.2, AC-F03-9, AC-F03-10).
 */

import React from 'react';
import { Modal, Text, TouchableOpacity, View } from 'react-native';

interface Props {
  visible: boolean;
  friendName: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

const RemoveFriendDialog: React.FC<Props> = ({
  visible,
  friendName,
  onConfirm,
  onCancel,
}) => {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View testID="remove-dialog">
        <Text testID="dialog-message">
          {`Xóa ${friendName ?? 'người dùng này'} khỏi danh sách bạn bè?`}
        </Text>
        <TouchableOpacity onPress={onConfirm} testID="confirm-button">
          <Text>Xóa</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={onCancel} testID="cancel-button">
          <Text>Hủy</Text>
        </TouchableOpacity>
      </View>
    </Modal>
  );
};

export default RemoveFriendDialog;
