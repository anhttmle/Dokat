/**
 * Tests for FeedScreen — mount load, ordering, refresh, empty, open.
 *
 * FeedService is mocked so the screen logic is tested in isolation.
 *
 * Refs: Design §6.7; FR-1, FR-2, FR-5, FR-7, FR-9;
 *       AC-F06-3, AC-F06-4, AC-F06-5, AC-F06-6
 */

import React from 'react';
import { act, fireEvent, render } from '@testing-library/react-native';

import FeedScreen from '../../screens/FeedScreen';

jest.mock('../../services/FeedService');

const makeItem = (id: string, seen = false) => ({
  post_id: id,
  sender_id: `s-${id}`,
  sender_display_name: `User ${id}`,
  sender_avatar_url: null,
  pet_name: null,
  cdn_url: `https://cdn/${id}.jpg`,
  created_at: new Date().toISOString(),
  seen,
});

describe('FeedScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('loads the feed on mount', async () => {
    const FeedService = require('../../services/FeedService').default;
    FeedService.getFeed.mockResolvedValue({ items: [], next_cursor: null });

    render(<FeedScreen />);
    await act(async () => {});

    expect(FeedService.getFeed).toHaveBeenCalledTimes(1);
  });

  it('renders items in the server-provided order', async () => {
    const FeedService = require('../../services/FeedService').default;
    FeedService.getFeed.mockResolvedValue({
      items: [makeItem('newer'), makeItem('older')],
      next_cursor: null,
    });

    const { findByTestId, getByTestId } = render(<FeedScreen />);
    await findByTestId('feed-item-newer');

    const list = getByTestId('feed-list');
    expect(list.props.data.map((i: { post_id: string }) => i.post_id)).toEqual([
      'newer',
      'older',
    ]);
  });

  it('reloads the feed on pull-to-refresh', async () => {
    const FeedService = require('../../services/FeedService').default;
    FeedService.getFeed.mockResolvedValue({
      items: [makeItem('p1')],
      next_cursor: null,
    });

    const { findByTestId, getByTestId } = render(<FeedScreen />);
    await findByTestId('feed-item-p1');

    await act(async () => {
      getByTestId('feed-list').props.refreshControl.props.onRefresh();
    });

    expect(FeedService.getFeed).toHaveBeenCalledTimes(2);
  });

  it('shows the empty state when there are no items', async () => {
    const FeedService = require('../../services/FeedService').default;
    FeedService.getFeed.mockResolvedValue({ items: [], next_cursor: null });

    const { findByTestId, getByText } = render(<FeedScreen />);
    await findByTestId('feed-empty-state');

    expect(
      getByText('Thêm bạn bè để xem ảnh thú cưng của họ'),
    ).toBeTruthy();
  });

  it('marks an item seen when opened', async () => {
    const FeedService = require('../../services/FeedService').default;
    FeedService.getFeed.mockResolvedValue({
      items: [makeItem('p1')],
      next_cursor: null,
    });
    FeedService.markSeen.mockResolvedValue(undefined);

    const { findByTestId } = render(<FeedScreen />);
    const row = await findByTestId('feed-item-p1');

    await act(async () => {
      fireEvent.press(row);
    });

    expect(FeedService.markSeen).toHaveBeenCalledWith('p1');
  });
});
