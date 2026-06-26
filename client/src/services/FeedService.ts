/**
 * FeedService — backend API client for the F06 feed.
 *
 * Responsibilities (Design §4.2):
 *   - getFeed(cursor?): GET /feed?cursor=&limit= → received posts
 *   - markSeen(postId): F07 integration point (DL-F06-02)
 *
 * Every request attaches a Firebase ID token via AuthService.getIdToken()
 * (same pattern as SocialService). ``markSeen`` delegates to
 * ``SeenService.markSeen`` (the F07 network call), keeping its signature
 * so FeedScreen's optimistic update is unchanged (DL-F07-05).
 */

import AuthService from './AuthService';
import SeenService from './SeenService';

const BASE_URL = 'http://localhost:8000';

/** One item on the feed (a received post). Design §2.1. */
export interface FeedItem {
  post_id: string;
  sender_id: string;
  sender_display_name: string | null;
  sender_avatar_url: string | null;
  pet_name: string | null;
  cdn_url: string;
  created_at: string;
  seen: boolean;
}

/** Result of GET /feed. Design §2.1. */
export interface FeedResult {
  items: FeedItem[];
  next_cursor: string | null;
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

const FeedService = {
  /**
   * Fetch one page of the current user's received feed.
   *
   * Design §3.1 — GET /feed
   *
   * @param cursor - Opaque cursor from a previous page (DL-F06-08);
   *   omit to load the first page.
   */
  getFeed: async (cursor?: string): Promise<FeedResult> => {
    const headers = await _authHeaders();
    const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : '';
    const resp = await fetch(`${BASE_URL}/feed${query}`, {
      method: 'GET',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'GET_FEED_FAILED');
    }
    return resp.json();
  },

  /**
   * Mark a post as seen by delegating to SeenService (DL-F07-05).
   *
   * FeedScreen updates the local ``seen`` flag optimistically and calls
   * this hook; the real ``POST /posts/{id}/seen`` lives in SeenService.
   * The signature is unchanged from the F06 boundary (DL-F06-02).
   *
   * @param postId - UUID of the post just opened full-screen.
   */
  markSeen: async (postId: string): Promise<void> => {
    await SeenService.markSeen(postId);
  },
};

export default FeedService;
