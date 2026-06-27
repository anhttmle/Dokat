/**
 * NotificationService — register FCM token and manage reminder preferences.
 *
 * Refs: Design §2.5, §3.1–§3.3, §4.2; AC-F09-4, AC-F09-5
 */

import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

export type ReminderType = 'feeding' | 'sleeping' | 'bathing' | 'playing';

/** All four reminder preferences keyed by type. */
export type NotificationPreferences = Record<ReminderType, boolean>;

interface RegisterTokenBody {
  fcm_token: string;
  timezone?: string;
}

interface SetPreferenceBody {
  enabled: boolean;
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

/**
 * Register or update the device FCM token with the current timezone.
 *
 * Sends the IANA timezone from `Intl.DateTimeFormat` unless explicitly
 * overridden. Backward-compatible with F03 (DL-F09-02).
 *
 * @param fcmToken - Firebase Cloud Messaging device token.
 * @param timezone - Optional IANA timezone override.
 */
async function registerToken(
  fcmToken: string,
  timezone?: string,
): Promise<void> {
  const tz =
    timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const body: RegisterTokenBody = { fcm_token: fcmToken, timezone: tz };
  const headers = await _authHeaders();
  const resp = await fetch(`${BASE_URL}/friends/fcm-token`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(body),
  });
  if (!resp.ok && resp.status !== 204) {
    throw new Error('REGISTER_TOKEN_FAILED');
  }
}

/**
 * Fetch all four reminder preference states for the current user.
 * Absent rows default to `true` server-side (opt-out model, AC-F09-4).
 */
async function getPreferences(): Promise<NotificationPreferences> {
  const headers = await _authHeaders();
  const resp = await fetch(`${BASE_URL}/notifications/preferences`, {
    method: 'GET',
    headers,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.error_code ?? 'GET_PREFERENCES_FAILED');
  }
  return resp.json() as Promise<NotificationPreferences>;
}

/**
 * Enable or disable a specific reminder type (idempotent, returns 204).
 *
 * @param type - Reminder category to toggle.
 * @param enabled - New state.
 */
async function setPreference(
  type: ReminderType,
  enabled: boolean,
): Promise<void> {
  const body: SetPreferenceBody = { enabled };
  const headers = await _authHeaders();
  const resp = await fetch(
    `${BASE_URL}/notifications/preferences/${type}`,
    { method: 'PUT', headers, body: JSON.stringify(body) },
  );
  if (!resp.ok && resp.status !== 204) {
    throw new Error('SET_PREFERENCE_FAILED');
  }
}

export const NotificationService = {
  registerToken,
  getPreferences,
  setPreference,
};
