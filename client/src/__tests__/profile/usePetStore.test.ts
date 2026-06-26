/**
 * Tests for usePetStore — Zustand pet state (Design §4.1).
 */

import type { Pet } from '../../services/ProfileService';
import usePetStore from '../../stores/usePetStore';

const _resetStore = (): void => {
  usePetStore.setState({ pets: [], activePetId: null, loading: false });
};

const samplePet: Pet = {
  id: 'pet-1',
  name: 'Mochi',
  species: 'dog',
  gender: 'male',
  birthdate: null,
  avatarUrl: null,
  createdAt: '2026-06-21T09:00:00Z',
};

describe('usePetStore', () => {
  beforeEach(() => {
    _resetStore();
  });

  it('has the expected initial state', () => {
    const state = usePetStore.getState();
    expect(state.pets).toEqual([]);
    expect(state.activePetId).toBeNull();
    expect(state.loading).toBe(false);
  });

  it('setPets replaces the pet list', () => {
    usePetStore.getState().setPets([samplePet]);
    expect(usePetStore.getState().pets).toEqual([samplePet]);
  });

  it('setActivePetId updates the active pet', () => {
    usePetStore.getState().setActivePetId('pet-1');
    expect(usePetStore.getState().activePetId).toBe('pet-1');
  });

  it('setLoading toggles the loading flag', () => {
    usePetStore.getState().setLoading(true);
    expect(usePetStore.getState().loading).toBe(true);
  });
});
