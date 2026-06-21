/**
 * PetSelectorChip — chip above the shutter button showing the pre-selected
 * pet on the camera UI (Design §4.1, DL-F02-06).
 *
 * Props:
 *   activePetId  – id of the currently selected pet, or null for "Không gán"
 *   pets         – list of available pets from usePetStore
 *   onOpenPicker – callback to open PetPickerOverlay
 */

import React from 'react';
import { Text, TouchableOpacity } from 'react-native';

interface Pet {
  id: string;
  name: string;
}

interface PetSelectorChipProps {
  activePetId: string | null;
  pets: Pet[];
  onOpenPicker: () => void;
}

const PetSelectorChip: React.FC<PetSelectorChipProps> = ({
  activePetId,
  pets,
  onOpenPicker,
}) => {
  const activePet = activePetId
    ? pets.find((p) => p.id === activePetId) ?? null
    : null;
  const label = activePet ? activePet.name : 'Không gán';

  return (
    <TouchableOpacity onPress={onOpenPicker} testID="pet-selector-chip">
      <Text>{label}</Text>
    </TouchableOpacity>
  );
};

export default PetSelectorChip;
