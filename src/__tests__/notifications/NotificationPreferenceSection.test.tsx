/**
 * Tests for NotificationPreferenceSection — 4 toggle rows.
 *
 * Refs: Design §6.8; AC-F09-4, AC-F09-5
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { NotificationPreferenceSection } from '../../components/NotificationPreferenceSection';
import { NotificationPreferences } from '../../services/NotificationService';

const ALL_TRUE: NotificationPreferences = {
  feeding: true,
  sleeping: true,
  bathing: true,
  playing: true,
};

const BATHING_OFF: NotificationPreferences = {
  feeding: true,
  sleeping: true,
  bathing: false,
  playing: true,
};

describe('NotificationPreferenceSection', () => {
  it('renders 4 toggle rows', () => {
    const { getByTestId } = render(
      <NotificationPreferenceSection
        preferences={ALL_TRUE}
        onToggle={jest.fn()}
      />,
    );

    expect(getByTestId('toggle-feeding')).toBeTruthy();
    expect(getByTestId('toggle-sleeping')).toBeTruthy();
    expect(getByTestId('toggle-bathing')).toBeTruthy();
    expect(getByTestId('toggle-playing')).toBeTruthy();
  });

  it('calls onToggle with type and new enabled state when toggled', () => {
    const onToggle = jest.fn();
    const { getByTestId } = render(
      <NotificationPreferenceSection
        preferences={ALL_TRUE}
        onToggle={onToggle}
      />,
    );

    fireEvent(getByTestId('toggle-bathing'), 'valueChange', false);

    expect(onToggle).toHaveBeenCalledWith('bathing', false);
  });

  it('reflects preference state from props', () => {
    const { getByTestId } = render(
      <NotificationPreferenceSection
        preferences={BATHING_OFF}
        onToggle={jest.fn()}
      />,
    );

    const toggle = getByTestId('toggle-bathing');
    expect(toggle.props.value).toBe(false);

    const feedingToggle = getByTestId('toggle-feeding');
    expect(feedingToggle.props.value).toBe(true);
  });
});
