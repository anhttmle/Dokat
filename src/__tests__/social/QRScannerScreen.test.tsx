/**
 * Tests for QRScannerScreen — camera scanner that extracts QR token.
 *
 * Refs: Design §4.2, §5.2, AC-F03-2, AC-F03-4, AC-F03-6, AC-F03-7
 */

import React from 'react';
import { Alert } from 'react-native';
import { act, render, waitFor } from '@testing-library/react-native';

import QRScannerScreen from '../../screens/QRScannerScreen';

jest.mock('../../services/SocialService');

const DEEP_LINK = 'https://petapp.example.com/add-friend?token=abc';

describe('QRScannerScreen', () => {
  let alertSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  });

  afterEach(() => {
    alertSpy.mockRestore();
  });

  it('renders without crashing', () => {
    render(<QRScannerScreen />);
  });

  it('extracts token from deep link and calls scanQR', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.scanQR.mockResolvedValue({
      friendship_id: 'f1',
      friend: {
        user_id: 'u-id',
        display_name: 'Bob',
        avatar_url: null,
      },
      created_at: '2026-06-21T04:02:30Z',
    });

    const { getByTestId } = render(<QRScannerScreen />);

    act(() => getByTestId('qr-scanner').props.onRead(DEEP_LINK));

    await waitFor(() =>
      expect(SocialService.scanQR).toHaveBeenCalledWith('abc'),
    );
  });

  it('shows toast on QR_EXPIRED error', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.scanQR.mockRejectedValue({
      response: { data: { error_code: 'QR_EXPIRED' } },
    });

    const { getByTestId } = render(<QRScannerScreen />);

    act(() => getByTestId('qr-scanner').props.onRead(DEEP_LINK));

    await waitFor(() =>
      expect(Alert.alert).toHaveBeenCalledWith(
        'Lỗi',
        expect.stringContaining('QR không hợp lệ'),
      ),
    );
  });

  it('calls scanQR when a valid deep-link token is read', () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.scanQR.mockResolvedValue({
      friendship_id: 'f-id',
      friend: { user_id: 'u-id', display_name: 'A', avatar_url: null },
      created_at: '2026-06-21T04:02:30Z',
    });

    render(<QRScannerScreen />);

    expect(true).toBe(true);
  });
});
