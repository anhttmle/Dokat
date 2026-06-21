/**
 * Tests for useFriendStore — Zustand store for friend state.
 *
 * Written TDD-style; tests are expected to FAIL until useFriendStore
 * is implemented in a later F03 task.
 *
 * Refs: Design §4.2, AC-F03-2, AC-F03-9
 */

import type { Friend } from '../../stores/useFriendStore';
import useFriendStore from '../../stores/useFriendStore';

jest.mock('../../services/SocialService');

const _resetStore = (): void => {
  useFriendStore.setState({
    friends: [],
    loading: false,
    error: null,
  });
};

const sampleFriend: Friend = {
  userId: 'friend-1',
  displayName: 'Tran Thi B',
  avatarUrl: null,
  friendshipCreatedAt: '2026-06-20T10:00:00Z',
};

describe('useFriendStore', () => {
  beforeEach(() => {
    _resetStore();
    jest.clearAllMocks();
  });

  it('has the expected initial state', () => {
    const state = useFriendStore.getState();
    expect(state.friends).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('setFriends replaces the friend list', () => {
    useFriendStore.getState().setFriends([sampleFriend]);
    expect(useFriendStore.getState().friends).toEqual([sampleFriend]);
  });

  it('setLoading toggles loading flag', () => {
    useFriendStore.getState().setLoading(true);
    expect(useFriendStore.getState().loading).toBe(true);
  });

  it('setError stores an error message', () => {
    useFriendStore.getState().setError('Something went wrong');
    expect(useFriendStore.getState().error).toBe('Something went wrong');
  });

  it('removeFriendLocally removes the friend from state', () => {
    useFriendStore.setState({ friends: [sampleFriend] });
    useFriendStore.getState().removeFriendLocally('friend-1');
    expect(useFriendStore.getState().friends).toEqual([]);
  });

  it('removeFriend removes friend from list optimistically', async () => {
    useFriendStore.setState({ friends: [sampleFriend] });
    useFriendStore.getState().removeFriend('friend-1');
    expect(useFriendStore.getState().friends).toHaveLength(0);
  });

  it('addFriend appends a friend to the list', () => {
    useFriendStore.getState().addFriend(sampleFriend);
    expect(useFriendStore.getState().friends).toEqual([sampleFriend]);
  });
});
