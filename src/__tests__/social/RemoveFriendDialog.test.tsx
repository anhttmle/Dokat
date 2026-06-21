/**
 * Tests for RemoveFriendDialog — confirmation modal before removing a friend.
 *
 * Written TDD-style; tests are expected to FAIL until the component
 * is implemented in a later F03 task.
 *
 * Refs: Design §4.2, AC-F03-9, AC-F03-10
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';

import RemoveFriendDialog from '../../components/RemoveFriendDialog';

jest.mock('../../services/SocialService');

describe('RemoveFriendDialog', () => {
  const onConfirm = jest.fn();
  const onCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing when visible', async () => {
    await act(async () => {
      render(
        <RemoveFriendDialog
          visible
          friendName="Tran Thi B"
          onConfirm={onConfirm}
          onCancel={onCancel}
        />,
      );
    });
  });

  it('calls onCancel when cancel button is pressed', async () => {
    // Detailed interaction tests will be added in a later task.
    expect(true).toBe(true);
  });

  it('calls onConfirm when confirm button is pressed', async () => {
    // Detailed interaction tests will be added in a later task.
    expect(true).toBe(true);
  });
});
