/**
 * HistoryService — backend API client for the F08 history.
 *
 * Responsibilities (Design §4.2):
 *   - getSent(cursor?): GET /history/sent?cursor=&limit= → sent posts
 *   - getReceived(cursor?): GET /history/received?cursor=&limit=
 *
 * Every request attaches a Firebase ID token via AuthService.getIdToken()
 * (same pattern as FeedService). F08 is read-only and never writes; the
 * "seen" writes belong to SeenService (F07, DL-F08-08).
 *
 * Refs: Design §1.1, §2.1, §4.2, §5; FR-1, FR-2; AC-F08-2; DL-F08-04
 */

import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

/** One photo the viewer sent within 24h (section "Đã gửi"). §2.1. */
export interface SentHistoryItem {
  post_id: string;
  cdn_url: string;
  created_at: string;
  recipient_count: number;
  seen_count: number;
}

/** One photo the viewer received within 24h (section "Đã nhận"). §2.1. */
export interface ReceivedHistoryItem {
  post_id: string;
  sender_id: string;
  sender_display_name: string | null;
  sender_avatar_url: string | null;
  pet_name: string | null;
  cdn_url: string;
  created_at: string;
  seen: boolean;
}

/** Result of GET /history/sent | /history/received. §2.1. */
export interface HistoryResult<TItem> {
  items: TItem[];
  next_cursor: string | null;
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

async function _getHistory<TItem>(
  path: string,
  cursor?: string,
): Promise<HistoryResult<TItem>> {
  const headers = await _authHeaders();
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : '';
  const resp = await fetch(`${BASE_URL}${path}${query}`, {
    method: 'GET',
    headers,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.error_code ?? 'GET_HISTORY_FAILED');
  }
  return resp.json();
}

const HistoryService = {
  /**
   * Fetch one page of the current user's sent history.
   *
   * Design §3.1 — GET /history/sent
   *
   * @param cursor - Opaque cursor from a previous page (DL-F08-04);
   *   omit to load the first page.
   */
  getSent: (cursor?: string): Promise<HistoryResult<SentHistoryItem>> =>
    _getHistory<SentHistoryItem>('/history/sent', cursor),

  /**
   * Fetch one page of the current user's received history.
   *
   * Design §3.2 — GET /history/received
   *
   * @param cursor - Opaque cursor from a previous page (DL-F08-04);
   *   omit to load the first page.
   */
  getReceived: (
    cursor?: string,
  ): Promise<HistoryResult<ReceivedHistoryItem>> =>
    _getHistory<ReceivedHistoryItem>('/history/received', cursor),
};

export default HistoryService;
