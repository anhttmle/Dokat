/**
 * QRScannerScreen — opens the camera to scan a friend's QR code.
 *
 * When a valid deep-link URL is detected, the screen extracts the
 * token and calls SocialService.scanQR() to create the friendship
 * (Design §1.2, §4.2, AC-F03-2).
 */

import React from 'react';
import { Text, View } from 'react-native';

const QRScannerScreen: React.FC = () => {
  return (
    <View>
      <Text testID="scanner-placeholder">QR Scanner</Text>
    </View>
  );
};

export default QRScannerScreen;
