/**
 * Tests for HistoryList — renders sent/received sections.
 *
 * Refs: Design §6.6; FR-3, FR-5; AC-F08-2
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import HistoryList from '../../components/HistoryList';
import type {
  ReceivedHistoryItem,
  SentHistoryItem,
} from '../../services/HistoryService';

const sentItem: SentHistoryItem = {
  post_id: 'p1',
  cdn_url: 'https://cdn/p1.jpg',
  created_at: new Date().toISOString(),
  recipient_count: 3,
  seen_count: 2,
};

const receivedItem: ReceivedHistoryItem = {
  post_id: 'p2',
  sender_id: 's2',
  sender_display_name: 'Anh',
  sender_avatar_url: null,
  pet_name: 'Mướp',
  cdn_url: 'https://cdn/p2.jpg',
  created_at: new Date().toISOString(),
  seen: false,
};

describe('HistoryList', () => {
  it('renders seen/total in sent mode (FR-3, FR-5)', () => {
    const { getByTestId } = render(
      <HistoryList title="Đã gửi" mode="sent" items={[sentItem]} />,
    );
    expect(getByTestId('history-seen-p1').props.children).toContain(
      '2/3 đã xem',
    );
  });

  it('renders the sender and pet in received mode (FR-3)', () => {
    const { getByTestId } = render(
      <HistoryList
        title="Đã nhận"
        mode="received"
        items={[receivedItem]}
      />,
    );
    expect(getByTestId('history-sender-p2').props.children).toContain('Anh');
    expect(getByTestId('history-sender-p2').props.children).toContain(
      'Mướp',
    );
  });

  it('shows the section empty label when there are no items', () => {
    const { getByTestId } = render(
      <HistoryList title="Đã gửi" mode="sent" items={[]} />,
    );
    expect(getByTestId('history-empty-sent')).toBeTruthy();
  });
});
