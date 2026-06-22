/**
 * Tests for SettingsScreen — account links, blocked list, logout.
 *
 * Refs: Design §1.1, §1.3, §1.5, §4.2, §6.10; FR-1, FR-2, FR-3, FR-8,
 *       FR-9, FR-10; AC-F10-3, AC-F10-6; DL-F10-07
 */

import React from 'react';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { useNavigation } from '@react-navigation/native';

import SettingsScreen from '../../screens/SettingsScreen';
import AuthService from '../../services/AuthService';
import LocalStorageService from '../../services/LocalStorageService';

jest.mock('@react-navigation/native', () => ({
  useNavigation: jest.fn(),
}));
jest.mock('../../services/SettingsService');
jest.mock('../../services/AuthService');
jest.mock('../../services/LocalStorageService');

const mockUseNavigation = useNavigation as jest.Mock;

describe('SettingsScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseNavigation.mockReturnValue({
      navigate: jest.fn(),
      reset: jest.fn(),
    });
    const SettingsService =
      require('../../services/SettingsService').default;
    SettingsService.listBlocked.mockResolvedValue({
      blocked: [],
      total: 0,
    });
  });

  it('renders three provider rows', async () => {
    const { getByTestId } = render(
      <SettingsScreen providers={['google']} />,
    );

    await act(async () => {});

    expect(getByTestId('account-link-apple')).toBeTruthy();
    expect(getByTestId('account-link-google')).toBeTruthy();
    expect(getByTestId('account-link-facebook')).toBeTruthy();
  });

  it('renders the blocked-user list with an unblock button', async () => {
    const SettingsService =
      require('../../services/SettingsService').default;
    SettingsService.listBlocked.mockResolvedValue({
      blocked: [
        {
          user_id: 'b-uuid',
          display_name: 'Beta',
          avatar_url: null,
          blocked_at: '2026-06-22T07:00:00Z',
        },
      ],
      total: 1,
    });

    const { findByText, getByTestId } = render(
      <SettingsScreen providers={['google']} />,
    );

    await findByText('Beta');
    expect(getByTestId('unblock-b-uuid')).toBeTruthy();
  });

  it('calls unblockUser when an unblock button is pressed', async () => {
    const SettingsService =
      require('../../services/SettingsService').default;
    SettingsService.listBlocked.mockResolvedValue({
      blocked: [
        {
          user_id: 'b-uuid',
          display_name: 'Beta',
          avatar_url: null,
          blocked_at: '2026-06-22T07:00:00Z',
        },
      ],
      total: 1,
    });
    SettingsService.unblockUser.mockResolvedValue(undefined);

    const { getByTestId } = render(
      <SettingsScreen providers={['google']} />,
    );

    await waitFor(() => getByTestId('unblock-b-uuid'));
    await act(async () => {
      fireEvent.press(getByTestId('unblock-b-uuid'));
    });

    expect(SettingsService.unblockUser).toHaveBeenCalledWith('b-uuid');
  });

  it('logs out: clears token + signs out + clears storage + navigates', async () => {
    const SettingsService =
      require('../../services/SettingsService').default;
    SettingsService.logout.mockResolvedValue(undefined);
    (AuthService.signOut as jest.Mock).mockResolvedValue(undefined);
    (LocalStorageService.clear as jest.Mock).mockResolvedValue([]);
    const navMock = { navigate: jest.fn(), reset: jest.fn() };
    mockUseNavigation.mockReturnValue(navMock);

    const { getByTestId } = render(
      <SettingsScreen providers={['google']} />,
    );

    await act(async () => {
      fireEvent.press(getByTestId('logout-button'));
    });
    await act(async () => {
      fireEvent.press(getByTestId('logout-confirm'));
    });

    expect(SettingsService.logout).toHaveBeenCalled();
    expect(AuthService.signOut).toHaveBeenCalled();
    expect(LocalStorageService.clear).toHaveBeenCalled();
    expect(navMock.navigate).toHaveBeenCalledWith('Onboarding');
  });
});
