/**
 * SettingsService — backend API client for F10 settings.
 *
 * Responsibilities (Design §3, §4.2):
 *   - unlinkProvider: DELETE /users/providers/{provider}
 *   - blockUser:      POST   /users/block
 *   - unblockUser:    DELETE /users/block/{id}
 *   - listBlocked:    GET    /users/block
 *   - reportUser:     POST   /users/report
 *   - logout:         POST   /users/logout
 *
 * Account linking is NOT here — it reuses AuthService.linkWithProvider
 * + POST /auth/link from F01 (DL-F10-01). All requests attach a Firebase
 * ID token via AuthService.getIdToken().
 */

import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

export type OAuthProviderName = 'apple' | 'google' | 'facebook';
export type ReportReason =
  | 'spam'
  | 'inappropriate'
  | 'harassment'
  | 'other';

export interface BlockedUserItem {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  blocked_at: string;
}

export interface BlockListResult {
  blocked: BlockedUserItem[];
  total: number;
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

const SettingsService = {
  /**
   * Unlink an OAuth provider from the current account.
   *
   * Design §3.1 — DELETE /users/providers/{provider}. The Firebase-side
   * unlink is performed separately by AuthService (DL-F10-02).
   */
  unlinkProvider: async (provider: OAuthProviderName): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(
      `${BASE_URL}/users/providers/${provider}`,
      { method: 'DELETE', headers },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'UNLINK_PROVIDER_FAILED');
    }
  },

  /**
   * Block a friend (silent — no notification, FR-5).
   *
   * Design §3.2 — POST /users/block.
   */
  blockUser: async (userId: string): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/users/block`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'BLOCK_FAILED');
    }
  },

  /**
   * Unblock a previously blocked user (idempotent — DL-F10-05).
   *
   * Design §3.3 — DELETE /users/block/{user_id}.
   */
  unblockUser: async (userId: string): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/users/block/${userId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'UNBLOCK_FAILED');
    }
  },

  /**
   * Fetch the current user's blocked-user list (DL-F10-09).
   *
   * Design §3.4 — GET /users/block.
   */
  listBlocked: async (): Promise<BlockListResult> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/users/block`, {
      method: 'GET',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'LIST_BLOCKED_FAILED');
    }
    return resp.json();
  },

  /**
   * Report a user with a fixed reason (AC-F10-5).
   *
   * Design §3.5 — POST /users/report.
   */
  reportUser: async (
    userId: string,
    reason: ReportReason,
  ): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/users/report`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId, reason }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'REPORT_FAILED');
    }
  },

  /**
   * Clear the backend device token on logout (DL-F10-07).
   *
   * Design §3.6 — POST /users/logout.
   */
  logout: async (): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/users/logout`, {
      method: 'POST',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'LOGOUT_FAILED');
    }
  },
};

export default SettingsService;
