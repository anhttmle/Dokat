/**
 * SendService — orchestrate the F05 send flow: presigned upload URL →
 * S3 PUT (with retry) → resolve location → confirm (POST /posts).
 *
 * The S3 PUT is wrapped in a retry of up to MAX_UPLOAD_RETRIES attempts
 * (FR-13, AC-F05-6). POST /posts is only called after a successful
 * upload, so a final upload failure leaves no post behind (AC-F05-7).
 * 0 recipients is valid and still creates a post (AC-F05-4). The native
 * binary PUT is injected via uploadBackend so the orchestration can be
 * unit-tested (DL-F05-08).
 *
 * Refs: Design §1.1, §1.4, §2.3, §4.2, §5; FR-5, FR-13;
 *       AC-F05-2, AC-F05-6, AC-F05-7; DL-F05-08; F11 (LocationService)
 */

import type { CapturedPhoto } from './capture/CaptureService';
import LocationService from './location/LocationService';
import { buildLocationPayload } from './location/locationPayload';
import AuthService from './AuthService';

const BASE_URL = 'http://localhost:8000';

/** Max S3 upload attempts before surfacing an error (FR-13). */
export const MAX_UPLOAD_RETRIES = 3;

/** Result of POST /posts/upload-url. */
export interface UploadUrlResult {
  upload_url: string;
  object_key: string;
  cdn_url: string;
}

/** Body sent to POST /posts. */
export interface CreatePostBody {
  s3_key: string;
  cdn_url: string;
  recipient_ids: string[];
  latitude?: number;
  longitude?: number;
}

/** Result of POST /posts. */
export interface CreatePostResult {
  post_id: string;
  expires_at: string;
  recipient_count: number;
  created_at: string;
}

/** Native PUT boundary; injectable for tests (DL-F05-08). */
export type UploadBackend = (
  uploadUrl: string,
  localUri: string,
) => Promise<void>;

export interface SendOptions {
  uploadBackend?: UploadBackend;
}

/** Default native S3 PUT: upload the local file's bytes (DL-F05-08). */
async function defaultUploadBackend(
  uploadUrl: string,
  localUri: string,
): Promise<void> {
  const file = await fetch(localUri);
  const blob = await file.blob();
  const resp = await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': 'image/jpeg' },
    body: blob,
  });
  if (!resp.ok) {
    throw new Error(`S3_UPLOAD_FAILED_${resp.status}`);
  }
}

async function _authHeaders(): Promise<Record<string, string>> {
  const token = await AuthService.getIdToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token ?? ''}`,
  };
}

async function _getUploadUrl(): Promise<UploadUrlResult> {
  const headers = await _authHeaders();
  const resp = await fetch(`${BASE_URL}/posts/upload-url`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content_type: 'image/jpeg' }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.error ?? 'UPLOAD_URL_FAILED');
  }
  return resp.json();
}

async function _uploadWithRetry(
  uploadBackend: UploadBackend,
  uploadUrl: string,
  localUri: string,
): Promise<void> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= MAX_UPLOAD_RETRIES; attempt += 1) {
    try {
      await uploadBackend(uploadUrl, localUri);
      return;
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError instanceof Error
    ? lastError
    : new Error('S3_UPLOAD_FAILED');
}

async function _confirm(
  body: CreatePostBody,
): Promise<CreatePostResult> {
  const headers = await _authHeaders();
  const resp = await fetch(`${BASE_URL}/posts`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const errBody = await resp.json().catch(() => ({}));
    throw new Error(errBody?.error_code ?? 'CREATE_POST_FAILED');
  }
  return resp.json();
}

const SendService = {
  /**
   * Send a captured photo to the chosen recipients.
   *
   * @param photo - The CapturedPhoto handed off from F04.
   * @param recipientIds - Chosen recipient UUIDs (may be empty — FR-4).
   * @param options - Optional injected uploadBackend (DL-F05-08).
   * @returns The created post metadata.
   */
  send: async (
    photo: CapturedPhoto,
    recipientIds: string[],
    options: SendOptions = {},
  ): Promise<CreatePostResult> => {
    const uploadBackend = options.uploadBackend ?? defaultUploadBackend;

    const { upload_url, object_key, cdn_url } = await _getUploadUrl();
    await _uploadWithRetry(uploadBackend, upload_url, photo.localUri);

    const location = await LocationService.getCurrentLocation();
    const latlng = buildLocationPayload(location);

    return _confirm({
      s3_key: object_key,
      cdn_url,
      recipient_ids: recipientIds,
      ...latlng,
    });
  },
};

export default SendService;
