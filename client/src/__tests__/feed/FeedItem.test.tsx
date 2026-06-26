/**
 * Tests for FeedItem — renders sender/pet, time and seen indicator.
 *
 * Refs: Design §6.6; FR-4, FR-6; AC-F06-3
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import FeedItem from '../../components/FeedItem';
import type { FeedItem as FeedItemData } from '../../services/FeedService';

const baseItem: FeedItemData = {
  post_id: 'p1',
  sender_id: 's1',
  sender_display_name: 'Anh',
  sender_avatar_url: null,
  pet_name: 'Mướp',
  cdn_url: 'https://cdn/p1.jpg',
  created_at: new Date().toISOString(),
  seen: false,
};

describe('FeedItem', () => {
  it('renders the sender and pet name', () => {
    const { getByTestId } = render(<FeedItem item={baseItem} />);
    expect(getByTestId('feed-sender-p1').props.children).toContain('Anh');
    expect(getByTestId('feed-sender-p1').props.children).toContain('Mướp');
  });

  it('shows the unseen indicator when seen=false', () => {
    const { getByTestId } = render(<FeedItem item={baseItem} />);
    expect(getByTestId('unseen-indicator-p1')).toBeTruthy();
  });

  it('hides the indicator when seen=true', () => {
    const { queryByTestId } = render(
      <FeedItem item={{ ...baseItem, seen: true }} />,
    );
    expect(queryByTestId('unseen-indicator-p1')).toBeNull();
  });
});
