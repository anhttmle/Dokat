/**
 * useProfileStore — Zustand store for owner profile state (Design §4.1).
 *
 * State:
 *   ownerProfile — current owner profile (nullable until loaded)
 *   loading      — true while a profile request is in flight
 */

import { create } from 'zustand';

import type { OwnerProfile } from '../services/ProfileService';

interface ProfileState {
  ownerProfile: OwnerProfile | null;
  loading: boolean;
  setOwnerProfile: (ownerProfile: OwnerProfile | null) => void;
  setLoading: (loading: boolean) => void;
}

const useProfileStore = create<ProfileState>((set) => ({
  ownerProfile: null,
  loading: false,

  setOwnerProfile: (ownerProfile) => set({ ownerProfile }),
  setLoading: (loading) => set({ loading }),
}));

export default useProfileStore;
