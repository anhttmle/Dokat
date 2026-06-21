/**
 * EditPetProfileSheet — bottom sheet to edit an existing pet
 * (Design §4.1).
 *
 * Props:
 *   pet       — existing pet to pre-fill the form.
 *   onUpdated — called with the updated Pet after submit.
 *   onDismiss — called when the sheet should close without saving.
 *
 * Sends only changed fields as partial update to ProfileService.patchPet.
 */

import React, { useState } from 'react';
import {
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import ProfileService from '../../services/ProfileService';
import type { Pet, PetGender, PetSpecies } from '../../services/ProfileService';

const SPECIES_LABELS: Record<PetSpecies, string> = {
  dog: 'Chó',
  cat: 'Mèo',
};

const GENDER_LABELS: Record<PetGender, string> = {
  male: 'Đực',
  female: 'Cái',
  unknown: 'Không rõ',
};

interface Props {
  pet?: Pet;
  onUpdated?: (pet: Pet) => void;
  onDismiss?: () => void;
}

const EditPetProfileSheet: React.FC<Props> = ({
  pet,
  onUpdated,
  onDismiss,
}) => {
  const [name, setName] = useState(pet?.name ?? '');
  const [species, setSpecies] = useState<PetSpecies>(
    pet?.species ?? 'dog',
  );
  const [gender, setGender] = useState<PetGender>(
    pet?.gender ?? 'unknown',
  );
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!pet || !name.trim()) return;
    setSubmitting(true);
    try {
      const patch: Partial<{
        name: string;
        species: PetSpecies;
        gender: PetGender;
      }> = {};
      if (name.trim() !== pet.name) patch.name = name.trim();
      if (species !== pet.species) patch.species = species;
      if (gender !== pet.gender) patch.gender = gender;

      const updated = await ProfileService.patchPet(pet.id, patch);
      onUpdated?.(updated);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View testID="edit-pet-profile-sheet">
      <TextInput
        testID="name-input"
        placeholder="Tên thú cưng"
        value={name}
        onChangeText={setName}
      />

      <Text testID="species-display">
        {SPECIES_LABELS[species]}
      </Text>

      {(['dog', 'cat'] as PetSpecies[]).map((s) => (
        <TouchableOpacity
          key={s}
          testID={`species-option-${s}`}
          onPress={() => setSpecies(s)}
        >
          <Text>{SPECIES_LABELS[s]}</Text>
        </TouchableOpacity>
      ))}

      <Text testID="gender-display">
        {GENDER_LABELS[gender]}
      </Text>

      {(['male', 'female', 'unknown'] as PetGender[]).map((g) => (
        <TouchableOpacity
          key={g}
          testID={`gender-option-${g}`}
          onPress={() => setGender(g)}
        >
          <Text>{GENDER_LABELS[g]}</Text>
        </TouchableOpacity>
      ))}

      <TouchableOpacity
        testID="submit-button"
        onPress={handleSubmit}
        disabled={submitting}
      >
        <Text>{submitting ? 'Đang lưu…' : 'Lưu'}</Text>
      </TouchableOpacity>

      {onDismiss && (
        <TouchableOpacity
          testID="dismiss-button"
          onPress={onDismiss}
        >
          <Text>Hủy</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

export default EditPetProfileSheet;
