/**
 * Tests for FriendListScreen — displays friends and triggers removal.
 *
 * Refs: Design §4.2, FR-9, FR-10, FR-11, AC-F03-9, AC-F03-10
 */

import React from 'react';
import { act, render } from '@testing-library/react-native';

import FriendListScreen from '../../screens/FriendListScreen';

jest.mock('../../services/SocialService');
// useFriendStore: não mockado — Zustand é pure JS, funciona bem em Jest.
// FriendListScreen só usa removeFriendLocally (ação de estado puro, sem API).

describe('FriendListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.getFriends.mockResolvedValue({ friends: [], total: 0 });

    render(<FriendListScreen />);
  });

  it('fetches and renders friend list on mount', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.getFriends.mockResolvedValue({
      friends: [
        {
          user_id: 'u1',
          display_name: 'Alice',
          avatar_url: null,
          friendship_created_at: '2026-06-21T00:00:00Z',
        },
      ],
      total: 1,
    });

    const { findByText } = render(<FriendListScreen />);

    await findByText('Alice');
  });

  it('calls getFriends on mount', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.getFriends.mockResolvedValue({ friends: [], total: 0 });

    render(<FriendListScreen />);

    await act(async () => {});

    expect(SocialService.getFriends).toHaveBeenCalledTimes(1);
  });
});
