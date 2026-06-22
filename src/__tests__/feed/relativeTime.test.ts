/**
 * Tests for formatRelativeTime — Vietnamese relative-time labels.
 *
 * Refs: Design §6.5; FR-4; AC-F06-1; DL-F06-07
 */

import { formatRelativeTime } from '../../components/relativeTime';

const NOW = new Date('2026-06-22T12:00:00Z');

describe('formatRelativeTime', () => {
  it('returns "vừa xong" for under a minute', () => {
    const iso = '2026-06-22T11:59:30Z';
    expect(formatRelativeTime(iso, NOW)).toBe('vừa xong');
  });

  it('returns "N phút trước" for minutes', () => {
    const iso = '2026-06-22T11:57:00Z';
    expect(formatRelativeTime(iso, NOW)).toBe('3 phút trước');
  });

  it('returns "N giờ trước" for hours', () => {
    const iso = '2026-06-22T10:00:00Z';
    expect(formatRelativeTime(iso, NOW)).toBe('2 giờ trước');
  });
});
