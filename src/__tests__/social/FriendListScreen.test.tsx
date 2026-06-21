/**
 * Tests for FriendListScreen — displays friends and triggers removal.
 *
 * Written TDD-style; tests are expected to FAIL until the screen is
 * implemented in a later F03 task.
 *
 * Refs: Design §4.2, AC-F03-9, AC-F03-10
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

import FriendListScreen from '../../screens/FriendListScreen';

jest.mock('../../services/SocialService');

describe('FriendListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.listFriends.mockResolvedValueOnce({
      friends: [],
      total: 0,
    });

    await act(async () => {
      render(<FriendListScreen />);
    });
  });

  it('calls listFriends on mount', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.listFriends.mockResolvedValueOnce({
      friends: [],
      total: 0,
    });

    await act(async () => {
      render(<FriendListScreen />);
    });

    expect(SocialService.listFriends).toHaveBeenCalledTimes(1);
  });
});
