/**
 * SeenService — backend API client for F07 "seen" state.
 *
 * Responsibilities (Design §4.2):
 *   - markSeen(postId): POST /posts/{id}/seen — idempotent (DL-F07-02)
 *   - getSeenBy(postId): GET /posts/{id}/seen-by → viewers + count
 *
 * Every request attaches a Firebase ID token via AuthService.getIdToken()
 * (same pattern as FeedService).
 *
 * Refs: Design §1.1, §1.2, §2.1, §3.1, §3.2, §4.2;
 *   FR-1, FR-3, FR-4; AC-F07-1, AC-F07-2; DL-F07-05
 */

import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

/** One person who has seen a post (for the Sender). Design §2.1. */
export interface SeenViewer {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  seen_at: string;
}

/** Result of GET /posts/{id}/seen-by. Design §2.1. */
export interface SeenByResult {
  post_id: string;
  seen_count: number;
  viewers: SeenViewer[];
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

const SeenService = {
  /**
   * Mark a post as seen for the current recipient.
   *
   * Design §3.1 — POST /posts/{id}/seen. Idempotent: calling it again
   * keeps the first-seen timestamp and never duplicates (DL-F07-02).
   *
   * @param postId - UUID of the post just opened full-screen.
   */
  markSeen: async (postId: string): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(
      `${BASE_URL}/posts/${encodeURIComponent(postId)}/seen`,
      { method: 'POST', headers },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'MARK_SEEN_FAILED');
    }
  },

  /**
   * Fetch the list of recipients who have seen a post (Sender only).
   *
   * Design §3.2 — GET /posts/{id}/seen-by.
   *
   * @param postId - UUID of the sender's post.
   */
  getSeenBy: async (postId: string): Promise<SeenByResult> => {
    const headers = await _authHeaders();
    const resp = await fetch(
      `${BASE_URL}/posts/${encodeURIComponent(postId)}/seen-by`,
      { method: 'GET', headers },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'GET_SEEN_BY_FAILED');
    }
    return resp.json();
  },
};

export default SeenService;
