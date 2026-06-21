/**
 * Tests for CreatePetProfileSheet (Design §4.1).
 *
 * PetAIService and ProfileService are mocked via manual mocks in
 * src/services/ai/__mocks__ and src/services/__mocks__.
 *
 * imageUri prop is used to skip Step 1 (image selection) so tests
 * can focus on AI pre-fill and form behaviour.
 */

import React from 'react';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';

import CreatePetProfileSheet from '../../components/profile/CreatePetProfileSheet';
import PetAIService from '../../services/ai/PetAIService';
import ProfileService from '../../services/ProfileService';

jest.mock('../../services/ProfileService');
jest.mock('../../services/ai/PetAIService');

const mockInfer = PetAIService.infer as jest.MockedFunction<
  typeof PetAIService.infer
>;
const mockCreatePet = ProfileService.createPet as jest.MockedFunction<
  typeof ProfileService.createPet
>;

const PET_STUB = {
  id: 'pet-1',
  name: 'Luna',
  species: 'cat' as const,
  gender: 'female' as const,
  birthdate: null,
  avatarUrl: null,
  createdAt: '2026-06-21T09:00:00Z',
};

describe('CreatePetProfileSheet', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    const { getByTestId } = render(<CreatePetProfileSheet />);
    expect(getByTestId('create-pet-profile-sheet')).toBeTruthy();
  });

  it('pre-fills species from AI result when imageUri is provided', async () => {
    mockInfer.mockResolvedValueOnce({
      species: 'cat',
      confidence: 0.91,
      gender: 'female',
      gender_confidence: 0.80,
    });

    const { getByTestId } = render(
      <CreatePetProfileSheet imageUri="file:///tmp/cat.jpg" />,
    );

    await waitFor(() => {
      expect(getByTestId('species-display')).toBeTruthy();
    });
    expect(getByTestId('species-display').props.children).toBe('Mèo');
  });

  it(
    'allows user to edit AI-filled species and calls createPet ' +
      'with the user-chosen value (AC-F02-4)',
    async () => {
      mockInfer.mockResolvedValueOnce({
        species: 'cat',
        confidence: 0.91,
        gender: undefined,
        gender_confidence: 0.55,
      });
      mockCreatePet.mockResolvedValueOnce(PET_STUB);

      const { getByTestId } = render(
        <CreatePetProfileSheet imageUri="file:///tmp/cat.jpg" />,
      );

      // Wait for form to appear after AI inference
      await waitFor(() => {
        const display = getByTestId('species-display');
        expect(display.props.children).toBe('Mèo');
      });

      // User corrects species to dog
      await act(async () => {
        fireEvent.press(getByTestId('species-option-dog'));
      });

      // Fill in a name so the form can be submitted
      fireEvent.changeText(getByTestId('name-input'), 'Mochi');

      await act(async () => {
        fireEvent.press(getByTestId('submit-button'));
      });

      expect(mockCreatePet).toHaveBeenCalledTimes(1);
      expect(mockCreatePet).toHaveBeenCalledWith(
        expect.objectContaining({ species: 'dog', name: 'Mochi' }),
      );
    },
  );
});
