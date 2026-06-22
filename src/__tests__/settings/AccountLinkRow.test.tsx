/**
 * Tests for AccountLinkRow — one provider's link status + actions.
 *
 * Refs: Design §4.2, §6.8; FR-1, FR-2, FR-3; AC-F10-1, AC-F10-2;
 *       DL-F10-01, DL-F10-02
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import AccountLinkRow from '../../components/AccountLinkRow';

jest.mock('../../services/SettingsService');
jest.mock('../../services/AuthService', () => ({
  __esModule: true,
  default: { linkWithProvider: jest.fn().mockResolvedValue(undefined) },
}));

describe('AccountLinkRow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows linked status when provider is linked', () => {
    const { getByText } = render(
      <AccountLinkRow provider="google" linked isOnlyProvider={false} />,
    );

    expect(getByText('Đã liên kết')).toBeTruthy();
  });

  it('shows a link button when provider is not linked', () => {
    const { getByText } = render(
      <AccountLinkRow
        provider="google"
        linked={false}
        isOnlyProvider={false}
      />,
    );

    expect(getByText('Liên kết')).toBeTruthy();
  });

  it('shows an error and does not unlink the only provider', () => {
    const SettingsService =
      require('../../services/SettingsService').default;
    const { getByText, getByTestId } = render(
      <AccountLinkRow provider="apple" linked isOnlyProvider />,
    );

    fireEvent.press(getByTestId('unlink-apple'));

    expect(getByText(/không thể hủy liên kết/i)).toBeTruthy();
    expect(SettingsService.unlinkProvider).not.toHaveBeenCalled();
  });
});
