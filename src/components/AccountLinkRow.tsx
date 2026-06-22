/**
 * AccountLinkRow — shows one OAuth provider's link status and actions.
 *
 * Linking reuses AuthService.linkWithProvider + POST /auth/link from F01
 * (DL-F10-01); unlinking calls SettingsService.unlinkProvider. Unlinking
 * the only remaining provider is blocked client-side with an inline
 * error to avoid account lock-out (AC-F10-2, DL-F10-02).
 *
 * Refs: Design §1.1, §4.2; FR-1, FR-2, FR-3; AC-F10-1, AC-F10-2
 */

import React from 'react';
import { Text, TouchableOpacity, View } from 'react-native';

import AuthService from '../services/AuthService';
import SettingsService, {
  OAuthProviderName,
} from '../services/SettingsService';

const PROVIDER_LABELS: Record<OAuthProviderName, string> = {
  apple: 'Apple',
  google: 'Google',
  facebook: 'Facebook',
};

interface Props {
  provider: OAuthProviderName;
  linked: boolean;
  isOnlyProvider: boolean;
  onChange?: () => void;
}

const AccountLinkRow: React.FC<Props> = ({
  provider,
  linked,
  isOnlyProvider,
  onChange,
}) => {
  const [error, setError] = React.useState<string | null>(null);

  const handleLink = React.useCallback(async () => {
    setError(null);
    await AuthService.linkWithProvider(provider);
    onChange?.();
  }, [provider, onChange]);

  const handleUnlink = React.useCallback(async () => {
    if (isOnlyProvider) {
      setError(
        'Không thể hủy liên kết provider duy nhất của tài khoản',
      );
      return;
    }
    setError(null);
    await SettingsService.unlinkProvider(provider);
    onChange?.();
  }, [provider, isOnlyProvider, onChange]);

  return (
    <View testID={`account-link-${provider}`}>
      <Text>{PROVIDER_LABELS[provider]}</Text>

      {linked ? (
        <View>
          <Text>Đã liên kết</Text>
          <TouchableOpacity
            testID={`unlink-${provider}`}
            onPress={handleUnlink}
          >
            <Text>Hủy liên kết</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <TouchableOpacity
          testID={`link-${provider}`}
          onPress={handleLink}
        >
          <Text>Liên kết</Text>
        </TouchableOpacity>
      )}

      {error !== null && <Text testID={`link-error-${provider}`}>{error}</Text>}
    </View>
  );
};

export default AccountLinkRow;
