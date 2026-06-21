/**
 * Tests for PetSelectorChip (Design §4.1, DL-F02-06).
 *
 * Written TDD-style; richer interaction assertions are added in later
 * F02 tasks. This smoke test verifies the chip renders.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import PetSelectorChip from '../../components/camera/PetSelectorChip';

describe('PetSelectorChip', () => {
  it('renders the fallback label when no pet is selected', () => {
    const { getByTestId } = render(<PetSelectorChip petName={null} />);
    expect(getByTestId('pet-selector-chip')).toBeTruthy();
  });

  it('renders the pet name when provided', () => {
    const { getByText } = render(<PetSelectorChip petName="Mochi" />);
    expect(getByText('Mochi')).toBeTruthy();
  });
});
