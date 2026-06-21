/**
 * ProfileScreen — displays owner profile + list of pet profiles.
 *
 * Tapping a pet item navigates to PetTimelineScreen.
 * (Design §4.1, FR-11, AC-F02-1, AC-F02-2, AC-F02-7)
 */

import React, { useEffect, useState } from 'react';
import {
  Button,
  FlatList,
  Image,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { useNavigation } from '@react-navigation/native';

import EditOwnerProfileSheet from '../../components/profile/EditOwnerProfileSheet';
import usePetStore from '../../stores/usePetStore';
import useProfileStore from '../../stores/useProfileStore';
import { type Pet } from '../../services/ProfileService';

const ProfileScreen: React.FC = () => {
  const { ownerProfile, loading, fetchProfile } = useProfileStore();
  const { pets, fetchPets } = usePetStore();
  const navigation = useNavigation<{ navigate: (screen: string, params: object) => void }>();
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchPets();
  }, [fetchProfile, fetchPets]);

  if (loading && !ownerProfile) {
    return (
      <View testID="profile-screen">
        <Text>Đang tải…</Text>
      </View>
    );
  }

  const handlePetPress = (pet: Pet) => {
    navigation.navigate('PetTimeline', { pet });
  };

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
      <FlatList
        testID="pet-list"
        data={pets}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            testID={`pet-item-${item.id}`}
            onPress={() => handlePetPress(item)}
          >
            {item.avatarUrl ? (
              <Image
                source={{ uri: item.avatarUrl }}
                style={{ width: 48, height: 48, borderRadius: 24 }}
              />
            ) : null}
            <Text>{item.name}</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
};

export default ProfileScreen;
