/**
 * Tests for PetSelectorChip + PetPickerOverlay
 * (Design §4.1; FR-10; AC-F02-6; DL-F02-06).
 *
 * Written TDD-style — Task 9.1 writes these tests first so they FAIL,
 * Task 9.2 implements the components to make them PASS.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import PetSelectorChip from '../../components/camera/PetSelectorChip';
import PetPickerOverlay from '../../components/camera/PetPickerOverlay';

const PETS = [{ id: 'pet-uuid-1', name: 'Mochi' }];

describe('PetSelectorChip', () => {
  it("shows 'Không gán' when no pet selected", () => {
    const { getByText } = render(
      <PetSelectorChip
        activePetId={null}
        pets={PETS}
        onOpenPicker={jest.fn()}
      />,
    );
    expect(getByText('Không gán')).toBeTruthy();
  });

  it('shows pet name when pet selected', () => {
    const { getByText } = render(
      <PetSelectorChip
        activePetId="pet-uuid-1"
        pets={PETS}
        onOpenPicker={jest.fn()}
      />,
    );
    expect(getByText('Mochi')).toBeTruthy();
  });

  it('tap PetSelectorChip calls onOpenPicker', () => {
    const onOpenPicker = jest.fn();
    const { getByTestId } = render(
      <PetSelectorChip
        activePetId={null}
        pets={PETS}
        onOpenPicker={onOpenPicker}
      />,
    );
    fireEvent.press(getByTestId('pet-selector-chip'));
    expect(onOpenPicker).toHaveBeenCalledTimes(1);
  });
});

describe('PetPickerOverlay', () => {
  it('selecting a pet calls onSelectPet with the correct pet_id', () => {
    const onSelectPet = jest.fn();
    const { getByTestId } = render(
      <PetPickerOverlay
        visible={true}
        pets={PETS}
        onSelectPet={onSelectPet}
        onClose={jest.fn()}
      />,
    );
    fireEvent.press(getByTestId('pet-item-pet-uuid-1'));
    expect(onSelectPet).toHaveBeenCalledWith('pet-uuid-1');
  });

  it("'Không gán' option calls onSelectPet(null)", () => {
    const onSelectPet = jest.fn();
    const { getByTestId } = render(
      <PetPickerOverlay
        visible={true}
        pets={PETS}
        onSelectPet={onSelectPet}
        onClose={jest.fn()}
      />,
    );
    fireEvent.press(getByTestId('pet-option-no-assign'));
    expect(onSelectPet).toHaveBeenCalledWith(null);
  });
});
