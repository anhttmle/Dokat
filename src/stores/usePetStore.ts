/**
 * usePetStore — Zustand store for pet state (Design §4.1).
 *
 * State:
 *   pets        — pet profiles owned by the current user
 *   activePetId — pet pre-selected on the camera UI (nullable)
 *   loading     — true while a pet request is in flight
 */

import { create } from 'zustand';

import type { Pet } from '../services/ProfileService';

interface PetState {
  pets: Pet[];
  activePetId: string | null;
  loading: boolean;
  setPets: (pets: Pet[]) => void;
  setActivePetId: (activePetId: string | null) => void;
  setLoading: (loading: boolean) => void;
}

const usePetStore = create<PetState>((set) => ({
  pets: [],
  activePetId: null,
  loading: false,

  setPets: (pets) => set({ pets }),
  setActivePetId: (activePetId) => set({ activePetId }),
  setLoading: (loading) => set({ loading }),
}));

export default usePetStore;
