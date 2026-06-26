/**
 * Tests for ForceLinkScreen.
 *
 * FR-6; AC-F01-4 (Design §4.1):
 *   - Full-screen shown when forceLinkRequired=true, not when false.
 *   - Back gesture / hardware back is disabled (beforeRemove prevented).
 *   - Successful OAuth link → setForceLinkRequired(false) → Feed visible.
 */

import React from 'react';
import { Text } from 'react-native';
import { act, fireEvent, render } from '@testing-library/react-native';
import { useNavigation } from '@react-navigation/native';

import AuthGuard from '../../components/auth/AuthGuard';
import ForceLinkScreen from '../../screens/auth/ForceLinkScreen';
import AuthService from '../../services/AuthService';
import useAuthStore from '../../stores/useAuthStore';

jest.mock('@react-navigation/native', () => ({
  useNavigation: jest.fn(),
}));
jest.mock('../../stores/useAuthStore');
jest.mock('../../services/AuthService');

const mockUseAuthStore = useAuthStore as unknown as jest.Mock;
const mockUseNavigation = useNavigation as jest.Mock;

// ---------------------------------------------------------------------------
// Shared navigation mock factory
// ---------------------------------------------------------------------------

function makeNavMock() {
  const addListener = jest.fn(
    (_event: string, _handler: unknown) => jest.fn(),
  );
  return { addListener, navigate: jest.fn(), goBack: jest.fn() };
}

// ---------------------------------------------------------------------------

describe('ForceLinkScreen — render via AuthGuard', () => {
  beforeEach(() => {
    mockUseNavigation.mockReturnValue(makeNavMock());
  });

  it('test_renders_when_force_link_required', () => {
    // AC-F01-4: forceLinkRequired=true → ForceLinkScreen is shown, not Feed.
    mockUseAuthStore.mockReturnValue({
      forceLinkRequired: true,
      setForceLinkRequired: jest.fn(),
    });

    const { getByTestId, queryByTestId } = render(
      <AuthGuard>
        <Text testID="feed">Feed</Text>
      </AuthGuard>,
    );

    expect(getByTestId('force-link-screen')).toBeTruthy();
    expect(queryByTestId('feed')).toBeNull();
  });

  it('test_not_rendered_when_not_required', () => {
    // AC-F01-4: forceLinkRequired=false → children (Feed) shown, not screen.
    mockUseAuthStore.mockReturnValue({
      forceLinkRequired: false,
      setForceLinkRequired: jest.fn(),
    });

    const { getByTestId, queryByTestId } = render(
      <AuthGuard>
        <Text testID="feed">Feed</Text>
      </AuthGuard>,
    );

    expect(getByTestId('feed')).toBeTruthy();
    expect(queryByTestId('force-link-screen')).toBeNull();
  });
});

// ---------------------------------------------------------------------------

describe('ForceLinkScreen — back navigation disabled', () => {
  it('test_back_button_disabled', () => {
    // AC-F01-4: beforeRemove event must be prevented so user cannot go back.
    const navMock = makeNavMock();
    mockUseNavigation.mockReturnValue(navMock);
    mockUseAuthStore.mockReturnValue({
      forceLinkRequired: true,
      setForceLinkRequired: jest.fn(),
    });

    render(<ForceLinkScreen />);

    // Verify the component registered a beforeRemove listener.
    expect(navMock.addListener).toHaveBeenCalledWith(
      'beforeRemove',
      expect.any(Function),
    );

    // Simulate the back gesture by calling the captured handler.
    const [, handler] = navMock.addListener.mock.calls[0] as [
      string,
      (e: { preventDefault: jest.Mock }) => void,
    ];
    const mockPreventDefault = jest.fn();
    handler({ preventDefault: mockPreventDefault });

    expect(mockPreventDefault).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------

describe('ForceLinkScreen — link success', () => {
  it('test_link_success_navigates_to_feed', async () => {
    // AC-F01-4: After successful link, setForceLinkRequired(false) is called.
    // AuthGuard then shows children (Feed) instead of ForceLinkScreen.
    const mockSetForceLinkRequired = jest.fn();
    mockUseNavigation.mockReturnValue(makeNavMock());
    mockUseAuthStore.mockReturnValue({
      forceLinkRequired: true,
      setForceLinkRequired: mockSetForceLinkRequired,
    });
    (AuthService.linkWithProvider as jest.Mock).mockResolvedValue(undefined);

    const { getByTestId } = render(<ForceLinkScreen />);

    await act(async () => {
      fireEvent.press(getByTestId('provider-google'));
    });

    expect(AuthService.linkWithProvider).toHaveBeenCalledWith('google');
    expect(mockSetForceLinkRequired).toHaveBeenCalledWith(false);
  });
});
