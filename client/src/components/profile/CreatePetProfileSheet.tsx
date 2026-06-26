/**
 * CreatePetProfileSheet — multi-step sheet: pick image → AI fill →
 * form → submit (Design §4.1).
 *
 * Props:
 *   imageUri  — skip Step 1 and run AI immediately on this URI;
 *               used by camera flow (F04) and tests.
 *   onCreated — called with the newly created Pet after submit.
 *   onDismiss — called when the sheet should close without saving.
 *
 * Steps:
 *   1. Pick image (camera / gallery) — skipped if imageUri is provided.
 *   2. AI inference → editable form (name, species, gender, birthdate).
 *   3. Submit → ProfileService.createPet.
 */

import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import PetAIService, {
  type AIInferenceResult,
} from '../../services/ai/PetAIService';
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
  imageUri?: string;
  onCreated?: (pet: Pet) => void;
  onDismiss?: () => void;
}

type Step = 'pick-image' | 'inferring' | 'form' | 'submitting';

const CreatePetProfileSheet: React.FC<Props> = ({
  imageUri,
  onCreated,
  onDismiss,
}) => {
  const [step, setStep] = useState<Step>(
    imageUri ? 'inferring' : 'pick-image',
  );
  const [aiResult, setAiResult] = useState<AIInferenceResult | null>(null);

  const [name, setName] = useState('');
  const [species, setSpecies] = useState<PetSpecies>('dog');
  const [gender, setGender] = useState<PetGender>('unknown');

  useEffect(() => {
    if (!imageUri) return;
    let cancelled = false;

    const runInference = async () => {
      try {
        const result = await PetAIService.infer(imageUri);
        if (cancelled) return;
        setAiResult(result);
        setSpecies(result.species);
        if (result.gender) {
          setGender(result.gender);
        }
        setStep('form');
      } catch {
        if (!cancelled) setStep('form');
      }
    };

    runInference();
    return () => {
      cancelled = true;
    };
  }, [imageUri]);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setStep('submitting');
    try {
      const pet = await ProfileService.createPet({
        name: name.trim(),
        species,
        gender,
        avatarUrl: null,
      });
      onCreated?.(pet);
    } finally {
      setStep('form');
    }
  };

  return (
    <View testID="create-pet-profile-sheet">
      {step === 'pick-image' && (
        <Text>Chọn ảnh thú cưng để bắt đầu</Text>
      )}

      {step === 'inferring' && (
        <ActivityIndicator testID="ai-loading" />
      )}

      {(step === 'form' || step === 'submitting') && (
        <View>
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
            disabled={step === 'submitting'}
          >
            <Text>
              {step === 'submitting' ? 'Đang lưu…' : 'Lưu'}
            </Text>
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
      )}

      {aiResult && (
        <Text testID="ai-confidence">
          {`Độ tin cậy: ${Math.round(aiResult.confidence * 100)}%`}
        </Text>
      )}
    </View>
  );
};

export default CreatePetProfileSheet;
