/**
 * Tests that FeedService.markSeen delegates to SeenService (DL-F07-05).
 *
 * SeenService is mocked so we verify only the delegation; the network
 * behaviour itself is covered by SeenService.test.ts.
 *
 * Refs: Design §4.2, §6.4; AC-F07-1; DL-F07-05
 */

import FeedService from '../../services/FeedService';
import SeenService from '../../services/SeenService';

jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: { getIdToken: jest.fn().mockResolvedValue('mock-token') },
}));
jest.mock('../../services/SeenService');

describe('FeedService.markSeen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (SeenService.markSeen as jest.Mock).mockResolvedValue(undefined);
  });

  it('delegates to SeenService.markSeen with the post id', async () => {
    await FeedService.markSeen('p1');

    expect(SeenService.markSeen).toHaveBeenCalledWith('p1');
  });
});
