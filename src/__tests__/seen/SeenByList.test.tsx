/**
 * Tests for SeenByList — renders the seen count + viewer names.
 *
 * Refs: Design §6.5; FR-3, FR-4; AC-F07-2; DL-F07-06
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import SeenByList from '../../components/SeenByList';
import type { SeenByResult } from '../../services/SeenService';

const baseResult: SeenByResult = {
  post_id: 'p1',
  seen_count: 2,
  viewers: [
    {
      user_id: 'u1',
      display_name: 'Châu',
      avatar_url: null,
      seen_at: '2026-06-22T07:05:00Z',
    },
    {
      user_id: 'u2',
      display_name: 'Bình',
      avatar_url: null,
      seen_at: '2026-06-22T07:02:00Z',
    },
  ],
};

describe('SeenByList', () => {
  it('renders the seen count (FR-4, AC-F07-2)', () => {
    const { getByText } = render(<SeenByList result={baseResult} />);
    expect(getByText('2 người đã xem')).toBeTruthy();
  });

  it('lists each viewer display name (FR-3, AC-F07-2)', () => {
    const { getByText } = render(<SeenByList result={baseResult} />);
    expect(getByText('Châu')).toBeTruthy();
    expect(getByText('Bình')).toBeTruthy();
  });

  it('shows an empty state when nobody has seen', () => {
    const empty: SeenByResult = {
      post_id: 'p1',
      seen_count: 0,
      viewers: [],
    };
    const { getByText } = render(<SeenByList result={empty} />);
    expect(getByText('Chưa có ai xem')).toBeTruthy();
  });
});
