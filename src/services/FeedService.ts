/**
 * FeedService — backend API client for the F06 feed.
 *
 * Responsibilities (Design §4.2):
 *   - getFeed(cursor?): GET /feed?cursor=&limit= → received posts
 *   - markSeen(postId): F07 integration point (DL-F06-02)
 *
 * Every request attaches a Firebase ID token via AuthService.getIdToken()
 * (same pattern as SocialService). ``markSeen`` is a no-op boundary in
 * F06: it lets FeedScreen update the seen flag optimistically while F07
 * later plugs in the real ``POST /posts/{id}/seen`` network call.
 */

import AuthService from './AuthService';

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
   * Mark a post as seen — F07 integration point (DL-F06-02).
   *
   * In F06 this is a no-op boundary: FeedScreen updates the local
   * ``seen`` flag optimistically and calls this hook. F07 will replace
   * the body with a real ``POST /posts/{id}/seen`` request.
   *
   * @param postId - UUID of the post just opened full-screen.
   */
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  markSeen: async (postId: string): Promise<void> => {
    // F07 will plug the network call here (DL-F06-02).
  },
};

export default FeedService;
