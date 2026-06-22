/**
 * SettingsScreen — account linking, blocked list, and logout.
 *
 * Renders an AccountLinkRow per provider (FR-1,2,3), the blocked-user
 * list with unblock actions (FR-8), and a logout flow that clears the
 * device token, signs out of Firebase, clears local storage, and
 * navigates to Onboarding (FR-9, FR-10, AC-F10-6, DL-F10-07).
 *
 * Refs: Design §1.1, §1.3, §1.5, §4.2; FR-1, FR-2, FR-3, FR-8, FR-9,
 *       FR-10; AC-F10-3, AC-F10-6; DL-F10-07
 */

import React from 'react';
import {
  FlatList,
  Modal,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';

import AccountLinkRow from '../components/AccountLinkRow';
import AuthService from '../services/AuthService';
import LocalStorageService from '../services/LocalStorageService';
import SettingsService, {
  BlockedUserItem,
  OAuthProviderName,
} from '../services/SettingsService';

const ALL_PROVIDERS: OAuthProviderName[] = ['apple', 'google', 'facebook'];

interface Props {
  providers: OAuthProviderName[];
}

const SettingsScreen: React.FC<Props> = ({ providers }) => {
  const navigation = useNavigation<{
    navigate: (route: string) => void;
  }>();

  const [blocked, setBlocked] = React.useState<BlockedUserItem[]>([]);
  const [confirmingLogout, setConfirmingLogout] = React.useState(false);

  React.useEffect(() => {
    SettingsService.listBlocked().then((data) => setBlocked(data.blocked));
  }, []);

  const handleUnblock = React.useCallback(async (userId: string) => {
    setBlocked((prev) => prev.filter((b) => b.user_id !== userId));
    await SettingsService.unblockUser(userId);
  }, []);

  const handleLogout = React.useCallback(async () => {
    setConfirmingLogout(false);
    await SettingsService.logout();
    await AuthService.signOut();
    await LocalStorageService.clear();
    navigation.navigate('Onboarding');
  }, [navigation]);

  return (
    <View testID="settings-screen">
      <Text>Liên kết tài khoản</Text>
      {ALL_PROVIDERS.map((provider) => {
        const linked = providers.includes(provider);
        return (
          <AccountLinkRow
            key={provider}
            provider={provider}
            linked={linked}
            isOnlyProvider={linked && providers.length === 1}
          />
        );
      })}

      <Text>Người dùng đã chặn</Text>
      <FlatList
        data={blocked}
        keyExtractor={(item) => item.user_id}
        renderItem={({ item }) => (
          <View testID={`blocked-${item.user_id}`}>
            <Text>{item.display_name ?? item.user_id}</Text>
            <TouchableOpacity
              testID={`unblock-${item.user_id}`}
              onPress={() => handleUnblock(item.user_id)}
            >
              <Text>Bỏ chặn</Text>
            </TouchableOpacity>
          </View>
        )}
        testID="blocked-list"
      />

      <TouchableOpacity
        testID="logout-button"
        onPress={() => setConfirmingLogout(true)}
      >
        <Text>Đăng xuất</Text>
      </TouchableOpacity>

      <Modal visible={confirmingLogout} transparent animationType="fade">
        <View testID="logout-confirm-dialog">
          <Text>Bạn có chắc muốn đăng xuất?</Text>
          <TouchableOpacity testID="logout-confirm" onPress={handleLogout}>
            <Text>Đăng xuất</Text>
          </TouchableOpacity>
          <TouchableOpacity
            testID="logout-cancel"
            onPress={() => setConfirmingLogout(false)}
          >
            <Text>Hủy</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  );
};

export default SettingsScreen;
