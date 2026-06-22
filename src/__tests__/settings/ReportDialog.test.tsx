/**
 * Tests for ReportDialog — pick a fixed reason and report a user.
 *
 * Refs: Design §4.2, §6.9; FR-6; AC-F10-5; DL-F10-06
 */

import React from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';

import ReportDialog from '../../components/ReportDialog';

jest.mock('../../services/SettingsService');

describe('ReportDialog', () => {
  const onClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the four fixed reason options', () => {
    const { getByTestId } = render(
      <ReportDialog visible userId="b-uuid" onClose={onClose} />,
    );

    expect(getByTestId('reason-spam')).toBeTruthy();
    expect(getByTestId('reason-inappropriate')).toBeTruthy();
    expect(getByTestId('reason-harassment')).toBeTruthy();
    expect(getByTestId('reason-other')).toBeTruthy();
  });

  it('calls reportUser with the selected reason on submit', async () => {
    const SettingsService =
      require('../../services/SettingsService').default;
    SettingsService.reportUser.mockResolvedValue(undefined);

    const { getByTestId } = render(
      <ReportDialog visible userId="b-uuid" onClose={onClose} />,
    );

    fireEvent.press(getByTestId('reason-spam'));
    fireEvent.press(getByTestId('report-submit'));

    await waitFor(() =>
      expect(SettingsService.reportUser).toHaveBeenCalledWith(
        'b-uuid',
        'spam',
      ),
    );
  });

  it('shows a confirmation message after submitting', async () => {
    const SettingsService =
      require('../../services/SettingsService').default;
    SettingsService.reportUser.mockResolvedValue(undefined);

    const { getByTestId, findByText } = render(
      <ReportDialog visible userId="b-uuid" onClose={onClose} />,
    );

    fireEvent.press(getByTestId('reason-harassment'));
    fireEvent.press(getByTestId('report-submit'));

    await findByText('Cảm ơn bạn đã báo cáo');
  });
});
