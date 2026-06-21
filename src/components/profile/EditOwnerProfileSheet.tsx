/**
 * EditOwnerProfileSheet — bottom sheet to edit display_name and avatar
 * (Design §4.1, FR-11, AC-F02-2).
 *
 * Props:
 *   ownerProfile — current profile; prefills display_name input
 *   onClose      — called after a successful save or cancel
 */

import React, { useState } from 'react';
import {
  ActivityIndicator,
  Button,
  Text,
  TextInput,
  View,
} from 'react-native';

import type { OwnerProfile } from '../../services/ProfileService';
import useProfileStore from '../../stores/useProfileStore';

interface Props {
  ownerProfile: OwnerProfile;
  onClose?: () => void;
}

const EditOwnerProfileSheet: React.FC<Props> = ({
  ownerProfile,
  onClose,
}) => {
  const [displayName, setDisplayName] = useState(
    ownerProfile.displayName ?? '',
  );
  const { patchProfile, loading } = useProfileStore();

  const handleSave = async () => {
    await patchProfile({ displayName: displayName || null });
    onClose?.();
  };

  return (
    <View testID="edit-owner-profile-sheet">
      <Text>Chỉnh sửa hồ sơ</Text>
      <TextInput
        testID="display-name-input"
        value={displayName}
        onChangeText={setDisplayName}
        placeholder="Tên hiển thị"
        accessibilityLabel="display_name"
      />
      {loading ? (
        <ActivityIndicator />
      ) : (
        <Button title="Lưu" onPress={handleSave} />
      )}
    </View>
  );
};

export default EditOwnerProfileSheet;
