/**
 * useProfileStore — Zustand store for owner profile state (Design §4.1).
 *
 * State:
 *   ownerProfile — current owner profile (nullable until loaded)
 *   loading      — true while a profile request is in flight
 *
 * Actions:
 *   fetchProfile  — load owner profile from API, update ownerProfile
 *   patchProfile  — partial update via API, update ownerProfile
 */

import { create } from 'zustand';

import type {
  OwnerProfile,
  PatchOwnerProfileInput,
} from '../services/ProfileService';
import ProfileService from '../services/ProfileService';

interface ProfileState {
  ownerProfile: OwnerProfile | null;
  loading: boolean;
  setOwnerProfile: (ownerProfile: OwnerProfile | null) => void;
  setLoading: (loading: boolean) => void;
  fetchProfile: () => Promise<void>;
  patchProfile: (input: PatchOwnerProfileInput) => Promise<void>;
}

const useProfileStore = create<ProfileState>((set) => ({
  ownerProfile: null,
  loading: false,

  setOwnerProfile: (ownerProfile) => set({ ownerProfile }),
  setLoading: (loading) => set({ loading }),

  fetchProfile: async () => {
    set({ loading: true });
    const ownerProfile = await ProfileService.getOwnerProfile();
    set({ ownerProfile, loading: false });
  },

  patchProfile: async (input: PatchOwnerProfileInput) => {
    set({ loading: true });
    const ownerProfile = await ProfileService.patchOwnerProfile(input);
    set({ ownerProfile, loading: false });
  },
}));

export default useProfileStore;
