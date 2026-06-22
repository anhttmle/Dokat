/**
 * relativeTime — format an absolute ISO timestamp into a Vietnamese
 * relative string ("vừa xong", "3 phút trước", "2 giờ trước").
 *
 * The backend returns absolute ISO 8601 timestamps; the relative string
 * is computed on the client so it is timezone-independent and easy to
 * unit-test (DL-F06-07).
 *
 * Refs: Design §4.2; FR-4; AC-F06-1; DL-F06-07
 */

const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;
const SECONDS_PER_DAY = 86400;

/**
 * Return a Vietnamese relative-time label for *iso* relative to *now*.
 *
 * @param iso - Absolute ISO 8601 timestamp (the post's created_at).
 * @param now - Reference time; defaults to the current time.
 */
export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const elapsedMs = now.getTime() - new Date(iso).getTime();
  const seconds = Math.max(0, Math.floor(elapsedMs / 1000));

  if (seconds < SECONDS_PER_MINUTE) {
    return 'vừa xong';
  }
  if (seconds < SECONDS_PER_HOUR) {
    const minutes = Math.floor(seconds / SECONDS_PER_MINUTE);
    return `${minutes} phút trước`;
  }
  if (seconds < SECONDS_PER_DAY) {
    const hours = Math.floor(seconds / SECONDS_PER_HOUR);
    return `${hours} giờ trước`;
  }
  const days = Math.floor(seconds / SECONDS_PER_DAY);
  return `${days} ngày trước`;
}

export default formatRelativeTime;
