/**
 * Tests for SendService — orchestrate upload-url → S3 PUT → POST /posts.
 *
 * Mocks AuthService, LocationService and the global fetch. The S3 PUT
 * is injected via the uploadBackend option (DL-F05-08).
 *
 * Refs: Design §6.4; FR-5, FR-13; AC-F05-2, AC-F05-4, AC-F05-6,
 *       AC-F05-7
 */

import type { CapturedPhoto } from '../../services/capture/CaptureService';
import LocationService from '../../services/location/LocationService';
import SendService from '../../services/SendService';

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: { getIdToken: jest.fn().mockResolvedValue('mock-token') },
}));

jest.mock('../../services/location/LocationService', () => ({
  __esModule: true,
  default: { getCurrentLocation: jest.fn() },
}));

const mockFetch = jest.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).fetch = mockFetch;

const mockGetLocation = LocationService.getCurrentLocation as jest.Mock;

const jsonResponse = (body: unknown, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

const UPLOAD_URL_STUB = {
  upload_url: 'https://pawsnap.s3/upload?sig=abc',
  object_key: 'posts/u/123.jpg',
  cdn_url: 'https://cdn.pawsnap.app/posts/u/123.jpg',
};

const CREATE_POST_STUB = {
  post_id: 'post-uuid',
  expires_at: '2026-06-23T00:43:00Z',
  recipient_count: 2,
  created_at: '2026-06-22T00:43:00Z',
};

const PHOTO: CapturedPhoto = {
  localUri: 'file://small.jpg',
  s3Key: 'posts/u/local.jpg',
  width: 1280,
  height: 720,
  capturedAt: '2026-06-22T00:00:00Z',
};

/** Queue fetch responses: upload-url first, then POST /posts. */
function queueUploadUrlAndConfirm(): void {
  mockFetch
    .mockResolvedValueOnce(jsonResponse(UPLOAD_URL_STUB))
    .mockResolvedValueOnce(jsonResponse(CREATE_POST_STUB, 201));
}

/** Return the parsed body of the POST /posts fetch call, if any. */
function confirmBody(): Record<string, unknown> | null {
  const call = mockFetch.mock.calls.find(
    ([url]) => typeof url === 'string' && url.endsWith('/posts'),
  );
  if (!call) {
    return null;
  }
  return JSON.parse(call[1].body);
}

describe('SendService.send', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetLocation.mockResolvedValue(null);
  });

  it('calls upload-url → S3 PUT → POST /posts in order', async () => {
    queueUploadUrlAndConfirm();
    const uploadBackend = jest.fn().mockResolvedValue(undefined);

    const result = await SendService.send(PHOTO, ['r1', 'r2'], {
      uploadBackend,
    });

    expect(mockFetch.mock.calls[0][0]).toContain('/posts/upload-url');
    expect(uploadBackend).toHaveBeenCalledWith(
      UPLOAD_URL_STUB.upload_url,
      PHOTO.localUri,
    );
    expect(mockFetch.mock.calls[1][0]).toMatch(/\/posts$/);
    expect(result).toEqual(CREATE_POST_STUB);
  });

  it('retries the upload up to 3 times then confirms once', async () => {
    queueUploadUrlAndConfirm();
    const uploadBackend = jest
      .fn()
      .mockRejectedValueOnce(new Error('net'))
      .mockRejectedValueOnce(new Error('net'))
      .mockResolvedValueOnce(undefined);

    await SendService.send(PHOTO, ['r1'], { uploadBackend });

    expect(uploadBackend).toHaveBeenCalledTimes(3);
    const confirmCalls = mockFetch.mock.calls.filter(([url]) =>
      String(url).endsWith('/posts'),
    );
    expect(confirmCalls).toHaveLength(1);
  });

  it('throws after 3 failed uploads and never calls POST /posts', async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(UPLOAD_URL_STUB));
    const uploadBackend = jest
      .fn()
      .mockRejectedValue(new Error('offline'));

    await expect(
      SendService.send(PHOTO, ['r1'], { uploadBackend }),
    ).rejects.toThrow();

    expect(uploadBackend).toHaveBeenCalledTimes(3);
    const confirmCalls = mockFetch.mock.calls.filter(([url]) =>
      String(url).endsWith('/posts'),
    );
    expect(confirmCalls).toHaveLength(0);
  });

  it('still calls POST /posts with empty recipient_ids', async () => {
    queueUploadUrlAndConfirm();
    const uploadBackend = jest.fn().mockResolvedValue(undefined);

    await SendService.send(PHOTO, [], { uploadBackend });

    expect(confirmBody()?.recipient_ids).toEqual([]);
  });

  it('merges location into the body when available, omits when null', async () => {
    // With coordinates.
    queueUploadUrlAndConfirm();
    mockGetLocation.mockResolvedValueOnce({
      latitude: 10.776215,
      longitude: 106.695058,
    });
    const uploadBackend = jest.fn().mockResolvedValue(undefined);

    await SendService.send(PHOTO, ['r1'], { uploadBackend });
    const withLoc = confirmBody();
    expect(withLoc?.latitude).toBe(10.776215);
    expect(withLoc?.longitude).toBe(106.695058);

    // Without coordinates.
    jest.clearAllMocks();
    mockGetLocation.mockResolvedValue(null);
    queueUploadUrlAndConfirm();

    await SendService.send(PHOTO, ['r1'], { uploadBackend });
    const withoutLoc = confirmBody();
    expect(withoutLoc).not.toHaveProperty('latitude');
    expect(withoutLoc).not.toHaveProperty('longitude');
  });
});
