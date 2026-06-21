/**
 * Tests for RemoveFriendDialog — confirmation modal before removing a friend.
 *
 * Refs: Design §4.2, AC-F03-9, AC-F03-10
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import RemoveFriendDialog from '../../components/RemoveFriendDialog';

jest.mock('../../services/SocialService');

describe('RemoveFriendDialog', () => {
  const onConfirm = jest.fn();
  const onCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing when visible', () => {
    render(
      <RemoveFriendDialog
        visible
        friendName="Tran Thi B"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
  });

  it('calls onConfirm when confirm button is pressed', () => {
    const { getByText } = render(
      <RemoveFriendDialog
        visible
        friendName="Alice"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    fireEvent.press(getByText('Xóa'));

    expect(onConfirm).toHaveBeenCalled();
  });

  it('does NOT call onConfirm on cancel', () => {
    const { getByText } = render(
      <RemoveFriendDialog
        visible
        friendName="Alice"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    fireEvent.press(getByText('Hủy'));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalled();
  });
});
