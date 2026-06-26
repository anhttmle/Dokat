/**
 * PetPickerOverlay — bottom sheet listing pets + "Tạo pet mới" +
 * "Không gán", shown when PetSelectorChip is tapped (Design §4.1,
 * DL-F02-06).
 *
 * Props:
 *   visible          – controls visibility
 *   pets             – list of available pets
 *   onSelectPet      – called with pet id (string) or null ("Không gán")
 *   onClose          – called after selection or dismiss
 *   onOpenCreatePet  – optional; called when user taps "Tạo pet mới"
 *                      (F04 wires this to CreatePetProfileSheet)
 */

import React from 'react';
import { Text, TouchableOpacity, View } from 'react-native';

interface Pet {
  id: string;
  name: string;
}

interface PetPickerOverlayProps {
  visible: boolean;
  pets: Pet[];
  onSelectPet: (petId: string | null) => void;
  onClose: () => void;
  onOpenCreatePet?: () => void;
}

const PetPickerOverlay: React.FC<PetPickerOverlayProps> = ({
  visible,
  pets,
  onSelectPet,
  onClose,
  onOpenCreatePet,
}) => {
  if (!visible) {
    return null;
  }

  const handleSelectPet = (petId: string) => {
    onSelectPet(petId);
    onClose();
  };

  const handleNoAssign = () => {
    onSelectPet(null);
    onClose();
  };

  const handleCreateNew = () => {
    onClose();
    onOpenCreatePet?.();
  };

  return (
    <View testID="pet-picker-overlay">
      {pets.map((pet) => (
        <TouchableOpacity
          key={pet.id}
          testID={`pet-item-${pet.id}`}
          onPress={() => handleSelectPet(pet.id)}
        >
          <Text>{pet.name}</Text>
        </TouchableOpacity>
      ))}
      <TouchableOpacity
        testID="pet-option-create-new"
        onPress={handleCreateNew}
      >
        <Text>Tạo pet mới</Text>
      </TouchableOpacity>
      <TouchableOpacity
        testID="pet-option-no-assign"
        onPress={handleNoAssign}
      >
        <Text>Không gán</Text>
      </TouchableOpacity>
    </View>
  );
};

export default PetPickerOverlay;
