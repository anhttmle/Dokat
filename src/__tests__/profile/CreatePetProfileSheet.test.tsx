/**
 * Tests for CreatePetProfileSheet (Design §4.1).
 *
 * Written TDD-style; assertions on the full multi-step flow are added
 * in later F02 tasks. This smoke test verifies the sheet renders.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import CreatePetProfileSheet from '../../components/profile/CreatePetProfileSheet';

jest.mock('../../services/ProfileService');
jest.mock('../../services/ai/PetAIService');

describe('CreatePetProfileSheet', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<CreatePetProfileSheet />);
    expect(getByTestId('create-pet-profile-sheet')).toBeTruthy();
  });
});
