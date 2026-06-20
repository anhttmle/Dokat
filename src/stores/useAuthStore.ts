/**
 * useAuthStore — Zustand store for global auth state.
 *
 * State (Design §4.1):
 *   user              — current Firebase user snapshot
 *   isAnonymous       — true until at least one OAuth provider is linked
 *   forceLinkRequired — true when backend signals force-link deadline passed
 */

import { create } from 'zustand';

interface AuthUser {
  uid: string;
  isAnonymous: boolean;
}

interface AuthState {
  user: AuthUser | null;
  isAnonymous: boolean;
  forceLinkRequired: boolean;
  providers: string[];
  setUser: (user: AuthUser | null) => void;
  setForceLinkRequired: (required: boolean) => void;
  setProviders: (providers: string[]) => void;
}

const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAnonymous: true,
  forceLinkRequired: false,
  providers: [],

  setUser: (user) =>
    set({
      user,
      isAnonymous: user?.isAnonymous ?? true,
    }),

  setForceLinkRequired: (forceLinkRequired) => set({ forceLinkRequired }),

  setProviders: (providers) => set({ providers }),
}));

export default useAuthStore;
