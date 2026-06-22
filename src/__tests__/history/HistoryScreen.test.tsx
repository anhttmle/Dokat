/**
 * Tests for HistoryScreen — mount load, two sections, empty, open→seen.
 *
 * HistoryService and SeenService are mocked so the screen logic is tested
 * in isolation.
 *
 * Refs: Design §6.7; FR-1, FR-3, FR-5, FR-6;
 *       AC-F08-2, AC-F08-3, AC-F08-4; DL-F08-08
 */

import React from 'react';
import { act, fireEvent, render } from '@testing-library/react-native';

import HistoryScreen from '../../screens/HistoryScreen';

jest.mock('../../services/HistoryService');
jest.mock('../../services/SeenService');

const makeSent = (id: string) => ({
  post_id: id,
  cdn_url: `https://cdn/${id}.jpg`,
  created_at: new Date().toISOString(),
  recipient_count: 2,
  seen_count: 1,
});

const makeReceived = (id: string) => ({
  post_id: id,
  sender_id: `s-${id}`,
  sender_display_name: `User ${id}`,
  sender_avatar_url: null,
  pet_name: null,
  cdn_url: `https://cdn/${id}.jpg`,
  created_at: new Date().toISOString(),
  seen: false,
});

const getHistoryService = () =>
  require('../../services/HistoryService').default;
const getSeenService = () => require('../../services/SeenService').default;

describe('HistoryScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('loads both sections on mount (FR-1)', async () => {
    const HistoryService = getHistoryService();
    HistoryService.getSent.mockResolvedValue({ items: [], next_cursor: null });
    HistoryService.getReceived.mockResolvedValue({
      items: [],
      next_cursor: null,
    });

    render(<HistoryScreen />);
    await act(async () => {});

    expect(HistoryService.getSent).toHaveBeenCalledTimes(1);
    expect(HistoryService.getReceived).toHaveBeenCalledTimes(1);
  });

  it('renders the two sections (FR-3, AC-F08-2)', async () => {
    const HistoryService = getHistoryService();
    HistoryService.getSent.mockResolvedValue({
      items: [makeSent('s1')],
      next_cursor: null,
    });
    HistoryService.getReceived.mockResolvedValue({
      items: [makeReceived('r1')],
      next_cursor: null,
    });

    const { findByTestId } = render(<HistoryScreen />);

    expect(await findByTestId('history-section-sent')).toBeTruthy();
    expect(await findByTestId('history-section-received')).toBeTruthy();
  });

  it('shows the empty state when both are empty (FR-6, AC-F08-4)', async () => {
    const HistoryService = getHistoryService();
    HistoryService.getSent.mockResolvedValue({ items: [], next_cursor: null });
    HistoryService.getReceived.mockResolvedValue({
      items: [],
      next_cursor: null,
    });

    const { findByTestId } = render(<HistoryScreen />);
    expect(await findByTestId('history-empty-state')).toBeTruthy();
  });

  it('opens a sent photo and shows the seen-by list (AC-F08-3)', async () => {
    const HistoryService = getHistoryService();
    const SeenService = getSeenService();
    HistoryService.getSent.mockResolvedValue({
      items: [makeSent('s1')],
      next_cursor: null,
    });
    HistoryService.getReceived.mockResolvedValue({
      items: [],
      next_cursor: null,
    });
    SeenService.getSeenBy.mockResolvedValue({
      post_id: 's1',
      seen_count: 1,
      viewers: [
        {
          user_id: 'u1',
          display_name: 'Châu',
          avatar_url: null,
          seen_at: new Date().toISOString(),
        },
      ],
    });

    const { findByTestId } = render(<HistoryScreen />);
    const row = await findByTestId('history-item-s1');

    await act(async () => {
      fireEvent.press(row);
    });

    expect(SeenService.getSeenBy).toHaveBeenCalledWith('s1');
    expect(await findByTestId('seen-by-list')).toBeTruthy();
  });

  it('opens a received photo and marks it seen (FR-5)', async () => {
    const HistoryService = getHistoryService();
    const SeenService = getSeenService();
    HistoryService.getSent.mockResolvedValue({ items: [], next_cursor: null });
    HistoryService.getReceived.mockResolvedValue({
      items: [makeReceived('r1')],
      next_cursor: null,
    });
    SeenService.markSeen.mockResolvedValue(undefined);

    const { findByTestId } = render(<HistoryScreen />);
    const row = await findByTestId('history-item-r1');

    await act(async () => {
      fireEvent.press(row);
    });

    expect(SeenService.markSeen).toHaveBeenCalledWith('r1');
  });
});
