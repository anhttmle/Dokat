/**
 * Tests for AddFriendScreen — QR display with countdown and auto-refresh.
 *
 * Written TDD-style; tests are expected to FAIL until the screen is
 * implemented in a later F03 task.
 *
 * Refs: Design §4.2, AC-F03-1, AC-F03-3
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

import AddFriendScreen from '../../screens/AddFriendScreen';

jest.mock('../../services/SocialService');

const GENERATE_QR_STUB = {
  token: '550e8400-e29b-41d4-a716-446655440000',
  deep_link:
    'https://petapp.example.com/add-friend?token=550e8400',
  expires_at: new Date(Date.now() + 300_000).toISOString(),
};

describe('AddFriendScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', async () => {
    await act(async () => {
      render(<AddFriendScreen />);
    });
  });

  it('calls generateQR on mount', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.generateQR.mockResolvedValueOnce(GENERATE_QR_STUB);

    await act(async () => {
      render(<AddFriendScreen />);
    });

    expect(SocialService.generateQR).toHaveBeenCalledTimes(1);
  });
});
