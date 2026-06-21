/**
 * useFriendStore — Zustand store for friend list state (Design §4.2).
 *
 * State:
 *   friends   — friend profiles for the current user
 *   loading   — true while a request is in flight
 *   error     — last error message, or null
 *
 * Async actions (fetchFriends, removeFriend) call SocialService and
 * keep local state in sync with optimistic updates.
 */

import { create } from 'zustand';

import SocialService from '../services/SocialService';

export interface Friend {
  userId: string;
  displayName: string | null;
  avatarUrl: string | null;
  friendshipCreatedAt: string;
}

interface FriendState {
  friends: Friend[];
  loading: boolean;
  error: string | null;

  setFriends: (friends: Friend[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  removeFriendLocally: (userId: string) => void;

  fetchFriends: () => Promise<void>;
  removeFriend: (friendUserId: string) => Promise<void>;
}

const useFriendStore = create<FriendState>((set) => ({
  friends: [],
  loading: false,
  error: null,

  setFriends: (friends) => set({ friends }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  removeFriendLocally: (userId) =>
    set((state) => ({
      friends: state.friends.filter((f) => f.userId !== userId),
    })),

  fetchFriends: async () => {
    set({ loading: true, error: null });
    try {
      const data = await SocialService.listFriends();
      const friends: Friend[] = data.friends.map((item) => ({
        userId: item.user_id,
        displayName: item.display_name,
        avatarUrl: item.avatar_url,
        friendshipCreatedAt: item.friendship_created_at,
      }));
      set({ friends });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'UNKNOWN_ERROR',
      });
    } finally {
      set({ loading: false });
    }
  },

  removeFriend: async (friendUserId) => {
    set((state) => ({
      friends: state.friends.filter((f) => f.userId !== friendUserId),
    }));
    try {
      await SocialService.removeFriend(friendUserId);
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'REMOVE_FAILED',
      });
    }
  },
}));

export default useFriendStore;
