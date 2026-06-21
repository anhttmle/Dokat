/**
 * SocialService — backend API client for F03 social graph.
 *
 * Responsibilities (Design §4.2):
 *   - generateQR: POST /friends/qr/generate
 *   - scanQR:     POST /friends/qr/scan
 *   - listFriends: GET /friends
 *   - removeFriend: DELETE /friends/{id}
 *
 * All requests attach a Firebase ID token via AuthService.getIdToken().
 */

import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

export interface GenerateQRResult {
  token: string;
  deep_link: string;
  expires_at: string;
}

export interface FriendInfo {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface ScanQRResult {
  friendship_id: string;
  friend: FriendInfo;
  created_at: string;
}

export interface FriendItem {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  friendship_created_at: string;
}

export interface FriendListResult {
  friends: FriendItem[];
  total: number;
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

const SocialService = {
  /**
   * Request a new QR OTP from the backend.
   *
   * Design §3.1 — POST /friends/qr/generate
   */
  generateQR: async (): Promise<GenerateQRResult> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/friends/qr/generate`, {
      method: 'POST',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json();
      throw new Error(body?.error_code ?? 'GENERATE_QR_FAILED');
    }
    return resp.json();
  },

  /**
   * Submit a scanned QR token to create a friendship.
   *
   * Design §3.2 — POST /friends/qr/scan
   *
   * @param token - UUID token extracted from the deep link URL.
   */
  scanQR: async (token: string): Promise<ScanQRResult> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/friends/qr/scan`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ token }),
    });
    if (!resp.ok) {
      const body = await resp.json();
      throw new Error(body?.error_code ?? 'SCAN_QR_FAILED');
    }
    return resp.json();
  },

  /**
   * Fetch the current user's friend list.
   *
   * Design §3.3 — GET /friends
   */
  listFriends: async (): Promise<FriendListResult> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/friends`, {
      method: 'GET',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json();
      throw new Error(body?.error_code ?? 'LIST_FRIENDS_FAILED');
    }
    return resp.json();
  },

  /**
   * Remove a friendship by friend's user ID.
   *
   * Design §3.4 — DELETE /friends/{friend_user_id}
   *
   * @param friendUserId - UUID of the friend to remove.
   */
  removeFriend: async (friendUserId: string): Promise<void> => {
    const headers = await _authHeaders();
    const resp = await fetch(`${BASE_URL}/friends/${friendUserId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body?.error_code ?? 'REMOVE_FRIEND_FAILED');
    }
  },
};

export default SocialService;
