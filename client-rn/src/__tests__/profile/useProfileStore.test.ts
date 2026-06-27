/**
 * Tests for useProfileStore — owner profile Zustand store (Design §4.1).
 *
 * Written TDD-style; test 3 ("sets ownerProfile after fetch") is expected
 * to FAIL until useProfileStore.fetchProfile is implemented (Task 7.2).
 */

import type { OwnerProfile } from '../../services/ProfileService';
import ProfileService from '../../services/ProfileService';
import useProfileStore from '../../stores/useProfileStore';

jest.mock('../../services/ProfileService');

const mockGetOwnerProfile =
  ProfileService.getOwnerProfile as jest.MockedFunction<
    typeof ProfileService.getOwnerProfile
  >;

const MOCK_PROFILE: OwnerProfile = {
  userId: 'user-1',
  displayName: 'Nguyen Van A',
  avatarUrl: null,
  isAnonymous: false,
  providers: ['google'],
};

const resetStore = (): void => {
  useProfileStore.setState({
    ownerProfile: null,
    loading: false,
  });
};

describe('useProfileStore', () => {
  beforeEach(() => {
    resetStore();
    jest.clearAllMocks();
  });

  it('sets ownerProfile after fetchProfile resolves', async () => {
    mockGetOwnerProfile.mockResolvedValueOnce(MOCK_PROFILE);

    await useProfileStore.getState().fetchProfile();

    expect(useProfileStore.getState().ownerProfile).toEqual(MOCK_PROFILE);
    expect(useProfileStore.getState().loading).toBe(false);
  });
});
