/**
 * AddFriendScreen — displays a QR code OTP with countdown timer.
 *
 * On mount and when the countdown reaches 0, the screen calls
 * SocialService.generateQR() to get a fresh QR token and resets
 * the countdown (auto-refresh, Design §1.1, §4.2, AC-F03-1, AC-F03-3).
 */

import React from 'react';
import { ActivityIndicator, Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import SocialService, {
  type GenerateQRResult,
} from '../services/SocialService';

const AddFriendScreen: React.FC = () => {
  const [qrData, setQrData] = React.useState<GenerateQRResult | null>(
    null,
  );
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadQR = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await SocialService.generateQR();
      setQrData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ERROR');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadQR();
  }, [loadQR]);

  React.useEffect(() => {
    if (!qrData?.expires_at) {
      return;
    }
    const msRemaining =
      new Date(qrData.expires_at).getTime() - Date.now();
    if (msRemaining <= 0) {
      loadQR();
      return;
    }
    const timer = setTimeout(() => {
      loadQR();
    }, msRemaining);
    return () => clearTimeout(timer);
  }, [qrData?.expires_at, loadQR]);

  if (loading && !qrData) {
    return <ActivityIndicator testID="loading-indicator" />;
  }

  return (
    <View>
      {error ? (
        <Text testID="error-text">{error}</Text>
      ) : qrData ? (
        <>
          {loading && <ActivityIndicator testID="loading-indicator" />}
          <View testID="qr-image">
            <QRCode value={qrData.deep_link} size={200} />
          </View>
          <Text testID="qr-token">{qrData.token}</Text>
        </>
      ) : null}
    </View>
  );
};

export default AddFriendScreen;
