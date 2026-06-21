/**
 * Tests for PetTimelineScreen (Design §3.10, §4.1; AC-F02-7).
 *
 * ProfileService is mocked via the manual mock in
 * src/services/__mocks__/ProfileService.ts.
 *
 * Navigation is mocked via @react-navigation/native so tests
 * can supply route.params without a real navigator.
 */

import React from 'react';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';

import PetTimelineScreen from '../../screens/profile/PetTimelineScreen';
import ProfileService from '../../services/ProfileService';

jest.mock('../../services/ProfileService');
jest.mock('@react-navigation/native', () => ({
  useRoute: jest.fn(),
}));

import { useRoute } from '@react-navigation/native';

const mockGetPetPhotos = ProfileService.getPetPhotos as jest.MockedFunction<
  typeof ProfileService.getPetPhotos
>;
const mockUseRoute = useRoute as jest.Mock;

const PET_STUB = {
  id: 'pet-1',
  name: 'Mochi',
  species: 'dog' as const,
  gender: 'male' as const,
  birthdate: null,
  avatarUrl: 'https://cdn.pawsnap.app/avatars/pets/pet-1/mochi.jpg',
  createdAt: '2026-06-21T09:00:00Z',
};

const PHOTOS_PAGE_1 = {
  petId: 'pet-1',
  photos: [
    {
      photoId: 'photo-1',
      cdnUrl: 'https://cdn.pawsnap.app/photos/1.jpg',
      takenAt: '2026-06-20T08:00:00Z',
    },
    {
      photoId: 'photo-2',
      cdnUrl: 'https://cdn.pawsnap.app/photos/2.jpg',
      takenAt: '2026-06-19T08:00:00Z',
    },
    {
      photoId: 'photo-3',
      cdnUrl: 'https://cdn.pawsnap.app/photos/3.jpg',
      takenAt: '2026-06-18T08:00:00Z',
    },
  ],
  nextCursor: '2026-06-18T08:00:00Z',
  hasMore: true,
};

const PHOTOS_PAGE_2 = {
  petId: 'pet-1',
  photos: [
    {
      photoId: 'photo-4',
      cdnUrl: 'https://cdn.pawsnap.app/photos/4.jpg',
      takenAt: '2026-06-10T08:00:00Z',
    },
  ],
  nextCursor: null,
  hasMore: false,
};

describe('PetTimelineScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRoute.mockReturnValue({ params: { pet: PET_STUB } });
  });

  it('PetTimelineScreen renders pet avatar and name in header', async () => {
    mockGetPetPhotos.mockResolvedValueOnce({
      petId: 'pet-1',
      photos: [],
      nextCursor: null,
      hasMore: false,
    });

    const { getByTestId } = render(<PetTimelineScreen />);

    await waitFor(() => {
      expect(getByTestId('pet-timeline-avatar')).toBeTruthy();
      expect(getByTestId('pet-timeline-name')).toBeTruthy();
    });

    expect(
      getByTestId('pet-timeline-avatar').props.source.uri,
    ).toBe(PET_STUB.avatarUrl);
    expect(getByTestId('pet-timeline-name').props.children).toBe(PET_STUB.name);
  });

  it('PetTimelineScreen renders photo grid from API response', async () => {
    mockGetPetPhotos.mockResolvedValueOnce(PHOTOS_PAGE_1);

    const { getAllByTestId } = render(<PetTimelineScreen />);

    await waitFor(() => {
      expect(getAllByTestId('timeline-photo-item')).toHaveLength(3);
    });
  });

  it('PetTimelineScreen loads next page on scroll to end', async () => {
    mockGetPetPhotos
      .mockResolvedValueOnce(PHOTOS_PAGE_1)
      .mockResolvedValueOnce(PHOTOS_PAGE_2);

    const { getByTestId } = render(<PetTimelineScreen />);

    await waitFor(() => {
      expect(mockGetPetPhotos).toHaveBeenCalledTimes(1);
      expect(mockGetPetPhotos).toHaveBeenCalledWith('pet-1', undefined, undefined);
    });

    await act(async () => {
      fireEvent(getByTestId('pet-timeline-list'), 'onEndReached');
    });

    await waitFor(() => {
      expect(mockGetPetPhotos).toHaveBeenCalledTimes(2);
      expect(mockGetPetPhotos).toHaveBeenNthCalledWith(
        2,
        'pet-1',
        undefined,
        PHOTOS_PAGE_1.nextCursor,
      );
    });
  });
});
