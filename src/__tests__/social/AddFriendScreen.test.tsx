/**
 * Tests for AddFriendScreen — QR display with countdown and auto-refresh.
 *
 * Refs: Design §4.2, AC-F03-1, AC-F03-3
 */

import React from 'react';
import { render, act, waitFor } from '@testing-library/react-native';

import AddFriendScreen from '../../screens/AddFriendScreen';

jest.mock('../../services/SocialService');
jest.mock('react-native-qrcode-svg', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    __esModule: true,
    default: ({ testID }: { testID?: string }) =>
      React.createElement(View, { testID }),
  };
});

const futureISO = new Date(Date.now() + 300_000).toISOString();
const GENERATE_QR_STUB = {
  token: '550e8400-e29b-41d4-a716-446655440000',
  deep_link: 'https://petapp.example.com/add-friend?token=550e8400',
  expires_at: futureISO,
};

describe('AddFriendScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('calls generateQR on mount and renders QR', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.generateQR.mockResolvedValue(GENERATE_QR_STUB);

    const { findByTestId } = render(<AddFriendScreen />);
    await findByTestId('qr-image');

    expect(SocialService.generateQR).toHaveBeenCalledTimes(1);
  });

  it('calls generateQR again when countdown reaches zero', async () => {
    jest.useFakeTimers();
    const nowPlusOneSecond = new Date(Date.now() + 1000).toISOString();
    const SocialService = require('../../services/SocialService').default;
    SocialService.generateQR.mockResolvedValue({
      token: 't',
      deep_link: 'https://...',
      expires_at: nowPlusOneSecond,
    });

    render(<AddFriendScreen />);

    await act(async () => {
      jest.advanceTimersByTime(1100);
    });

    await waitFor(() =>
      expect(SocialService.generateQR).toHaveBeenCalledTimes(2),
    );
  });
});
