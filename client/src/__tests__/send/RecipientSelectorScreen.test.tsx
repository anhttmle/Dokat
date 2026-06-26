/**
 * Tests for RecipientSelectorScreen — default-select, toggle, and send.
 *
 * Mocks SocialService.getFriends and SendService.send.
 *
 * Refs: Design §6.5; FR-2, FR-3, FR-4; AC-F05-1, AC-F05-3, AC-F05-4
 */

import React from 'react';
import {
  act,
  fireEvent,
  render,
  waitFor,
} from '@testing-library/react-native';

import type { CapturedPhoto } from '../../services/capture/CaptureService';
import RecipientSelectorScreen from '../../screens/RecipientSelectorScreen';

jest.mock('../../services/SocialService');
jest.mock('../../services/SendService');

const PHOTO: CapturedPhoto = {
  localUri: 'file://small.jpg',
  s3Key: 'posts/u/local.jpg',
  width: 1280,
  height: 720,
  capturedAt: '2026-06-22T00:00:00Z',
};

const FRIENDS = {
  friends: [
    {
      user_id: 'u1',
      display_name: 'Alice',
      avatar_url: null,
      friendship_created_at: '2026-06-21T00:00:00Z',
    },
    {
      user_id: 'u2',
      display_name: 'Bob',
      avatar_url: null,
      friendship_created_at: '2026-06-21T00:00:00Z',
    },
  ],
  total: 2,
};

function getSocial() {
  return require('../../services/SocialService').default;
}

function getSend() {
  return require('../../services/SendService').default;
}

describe('RecipientSelectorScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getSocial().getFriends.mockResolvedValue(FRIENDS);
    getSend().send.mockResolvedValue({
      post_id: 'p1',
      expires_at: '2026-06-23T00:00:00Z',
      recipient_count: 2,
      created_at: '2026-06-22T00:00:00Z',
    });
  });

  it('selects all friends by default on mount', async () => {
    const { getByTestId } = render(
      <RecipientSelectorScreen photo={PHOTO} />,
    );

    await waitFor(() => getByTestId('recipient-u1'));
    expect(
      getByTestId('recipient-u1').props.accessibilityState.selected,
    ).toBe(true);
    expect(
      getByTestId('recipient-u2').props.accessibilityState.selected,
    ).toBe(true);
  });

  it('deselects a recipient when toggled', async () => {
    const { getByTestId } = render(
      <RecipientSelectorScreen photo={PHOTO} />,
    );

    await waitFor(() => getByTestId('recipient-u1'));
    fireEvent.press(getByTestId('recipient-u1'));

    expect(
      getByTestId('recipient-u1').props.accessibilityState.selected,
    ).toBe(false);
    expect(
      getByTestId('recipient-u2').props.accessibilityState.selected,
    ).toBe(true);
  });

  it('keeps send enabled with 0 recipients and sends an empty list', async () => {
    const { getByTestId } = render(
      <RecipientSelectorScreen photo={PHOTO} />,
    );

    await waitFor(() => getByTestId('recipient-u1'));
    fireEvent.press(getByTestId('recipient-u1'));
    fireEvent.press(getByTestId('recipient-u2'));

    await act(async () => {
      fireEvent.press(getByTestId('send-button'));
    });

    expect(getSend().send).toHaveBeenCalledWith(PHOTO, []);
  });

  it('invokes SendService.send with selected ids on press', async () => {
    const { getByTestId } = render(
      <RecipientSelectorScreen photo={PHOTO} />,
    );

    await waitFor(() => getByTestId('recipient-u1'));

    await act(async () => {
      fireEvent.press(getByTestId('send-button'));
    });

    expect(getSend().send).toHaveBeenCalledTimes(1);
    const [, ids] = getSend().send.mock.calls[0];
    expect(new Set(ids)).toEqual(new Set(['u1', 'u2']));
  });
});
