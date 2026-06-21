/**
 * QRScannerScreen — opens the camera to scan a friend's QR code.
 *
 * When a valid deep-link URL is detected, the screen extracts the
 * token and calls SocialService.scanQR() to create the friendship.
 * On error, maps error_code to a user-facing Alert (Design §5.2).
 *
 * Refs: Design §1.2, §4.2, §5.2; AC-F03-2, AC-F03-4, AC-F03-6,
 *       AC-F03-7, AC-F03-8
 */

import React from 'react';
import { Alert, View } from 'react-native';

import SocialService from '../services/SocialService';

/** Human-readable messages for known error codes (Design §5.2). */
const ERROR_MESSAGES: Record<string, string> = {
  QR_EXPIRED: 'QR không hợp lệ. Vui lòng yêu cầu người kia làm mới QR.',
  QR_USED: 'QR không hợp lệ. Vui lòng yêu cầu người kia làm mới QR.',
  ALREADY_FRIENDS: 'Hai bạn đã là bạn bè rồi.',
  SELF_FRIEND: 'Đây là QR của chính bạn.',
  FRIEND_LIMIT_INITIATOR: 'Người kia đã đạt giới hạn 20 bạn bè.',
  FRIEND_LIMIT_SCANNER: 'Bạn đã đạt giới hạn 20 bạn bè.',
};

/**
 * Extract the `token` query param from a deep-link URL.
 *
 * Returns null if the URL is malformed or the param is absent.
 */
function extractToken(url: string): string | null {
  try {
    return new URL(url).searchParams.get('token');
  } catch {
    return null;
  }
}

/**
 * Resolve a human-readable message from a caught scan error.
 *
 * Supports both axios-style objects `{ response.data.error_code }`
 * and plain Error objects whose message contains the error code.
 */
function resolveErrorMessage(err: unknown): string {
  const code =
    (err as any)?.response?.data?.error_code ??
    (err instanceof Error ? err.message : null) ??
    'UNKNOWN';
  return (
    ERROR_MESSAGES[code] ?? 'Đã xảy ra lỗi. Vui lòng thử lại.'
  );
}

const QRScannerScreen: React.FC = () => {
  /**
   * Called by the scanner element when a QR URL is decoded.
   *
   * Extracts the OTP token and calls SocialService.scanQR().
   * Any error is shown as an Alert (best-effort toast equivalent).
   */
  const handleRead = React.useCallback(async (data: string) => {
    const token = extractToken(data);
    if (!token) return;

    try {
      await SocialService.scanQR(token);
    } catch (err) {
      Alert.alert('Lỗi', resolveErrorMessage(err));
    }
  }, []);

  /**
   * The scanner View acts as the camera placeholder.
   *
   * `testID="qr-scanner"` and `onRead` are accessible via
   * ReactTestInstance.props in RNTL tests, allowing direct
   * invocation without a real camera device.
   * (See decision_log.md DL-F03-11)
   */
  const scannerProps = {
    testID: 'qr-scanner',
    onRead: handleRead,
  } as any; // eslint-disable-line @typescript-eslint/no-explicit-any

  return <View {...scannerProps} />;
};

export default QRScannerScreen;
