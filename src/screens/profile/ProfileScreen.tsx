/**
 * ProfileScreen — displays owner profile and a button to open the
 * EditOwnerProfileSheet (Design §4.1, FR-11, AC-F02-1, AC-F02-2).
 */

import React, { useEffect, useState } from 'react';
import {
  Button,
  Image,
  Text,
  View,
} from 'react-native';

import EditOwnerProfileSheet from '../../components/profile/EditOwnerProfileSheet';
import useProfileStore from '../../stores/useProfileStore';

const ProfileScreen: React.FC = () => {
  const { ownerProfile, loading, fetchProfile } = useProfileStore();
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  if (loading && !ownerProfile) {
    return (
      <View testID="profile-screen">
        <Text>Đang tải…</Text>
      </View>
    );
  }

  return (
    <View testID="profile-screen">
      {ownerProfile?.avatarUrl ? (
        <Image
          testID="owner-avatar"
          source={{ uri: ownerProfile.avatarUrl }}
          style={{ width: 80, height: 80, borderRadius: 40 }}
        />
      ) : null}
      <Text testID="owner-display-name">
        {ownerProfile?.displayName ?? '—'}
      </Text>
      <Button
        title="Chỉnh sửa"
        onPress={() => setEditing(true)}
      />
      {editing && ownerProfile ? (
        <EditOwnerProfileSheet
          ownerProfile={ownerProfile}
          onClose={() => setEditing(false)}
        />
      ) : null}
    </View>
  );
};

export default ProfileScreen;
