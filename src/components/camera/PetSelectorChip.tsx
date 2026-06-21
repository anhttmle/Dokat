/**
 * PetSelectorChip — small chip above the shutter button showing the
 * pre-selected pet on the camera UI (Design §4.1, DL-F02-06).
 *
 * Skeleton for F02 task 1.2; full styling lands in later tasks.
 */

import React from 'react';
import { Text, TouchableOpacity } from 'react-native';

interface PetSelectorChipProps {
  petName?: string | null;
  onPress?: () => void;
}

const PetSelectorChip: React.FC<PetSelectorChipProps> = ({
  petName,
  onPress,
}) => {
  return (
    <TouchableOpacity onPress={onPress} testID="pet-selector-chip">
      <Text>{petName ?? 'Không gán'}</Text>
    </TouchableOpacity>
  );
};

export default PetSelectorChip;
