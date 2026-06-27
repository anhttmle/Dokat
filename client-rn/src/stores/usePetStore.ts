/**
 * usePetStore — Zustand store for pet state (Design §4.1).
 *
 * State:
 *   pets        — pet profiles owned by the current user
 *   activePetId — pet pre-selected on the camera UI (nullable)
 *   loading     — true while a pet request is in flight
 *
 * Async actions (fetchPets, createPet, updatePet) call ProfileService
 * and keep local state in sync.
 */

import { create } from 'zustand';

import ProfileService, {
  type CreatePetInput,
  type PatchPetInput,
  type Pet,
} from '../services/ProfileService';

interface PetState {
  pets: Pet[];
  activePetId: string | null;
  loading: boolean;

  setPets: (pets: Pet[]) => void;
  setActivePetId: (activePetId: string | null) => void;
  setLoading: (loading: boolean) => void;

  fetchPets: () => Promise<void>;
  createPet: (input: CreatePetInput) => Promise<Pet>;
  updatePet: (petId: string, input: PatchPetInput) => Promise<Pet>;
}

const usePetStore = create<PetState>((set) => ({
  pets: [],
  activePetId: null,
  loading: false,

  setPets: (pets) => set({ pets }),
  setActivePetId: (activePetId) => set({ activePetId }),
  setLoading: (loading) => set({ loading }),

  fetchPets: async () => {
    set({ loading: true });
    try {
      const pets = await ProfileService.listPets();
      set({ pets });
    } finally {
      set({ loading: false });
    }
  },

  createPet: async (input) => {
    set({ loading: true });
    try {
      const pet = await ProfileService.createPet(input);
      set((state) => ({ pets: [...state.pets, pet] }));
      return pet;
    } finally {
      set({ loading: false });
    }
  },

  updatePet: async (petId, input) => {
    set({ loading: true });
    try {
      const updated = await ProfileService.patchPet(petId, input);
      set((state) => ({
        pets: state.pets.map((p) => (p.id === petId ? updated : p)),
      }));
      return updated;
    } finally {
      set({ loading: false });
    }
  },

}));

export default usePetStore;
