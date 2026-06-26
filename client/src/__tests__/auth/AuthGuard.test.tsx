/**
 * Tests for AuthGuard component and useRequireLinked hook.
 * AuthGuard renders ForceLinkScreen when forceLinkRequired=true (AC-F01-4).
 * useRequireLinked gates actions behind OAuth linking (AC-F01-2, AC-F01-3).
 *
 * Design ref: §4.1
 */

import React from 'react';
import { Text, TouchableOpacity } from 'react-native';
import { act, fireEvent, render } from '@testing-library/react-native';

jest.mock('@react-navigation/native', () => ({
  useNavigation: () => ({
    addListener: jest.fn(() => jest.fn()),
    navigate: jest.fn(),
    goBack: jest.fn(),
  }),
}));

import AuthGuard, {
  useRequireLinked,
} from '../../components/auth/AuthGuard';
import LinkAccountSheet from '../../components/auth/LinkAccountSheet';
import AuthService from '../../services/AuthService';
import useAuthStore from '../../stores/useAuthStore';

jest.mock('../../stores/useAuthStore');
jest.mock('../../services/AuthService');

const mockUseAuthStore = useAuthStore as unknown as jest.Mock;

describe('AuthGuard', () => {
  describe('when forceLinkRequired is false', () => {
    beforeEach(() => {
      mockUseAuthStore.mockReturnValue({
        isAnonymous: false,
        forceLinkRequired: false,
      });
    });

    it('renders children', () => {
      const { getByText } = render(
        <AuthGuard>
          <Text>Protected content</Text>
        </AuthGuard>,
      );

      expect(getByText('Protected content')).toBeTruthy();
    });

    it('does not render ForceLinkScreen', () => {
      const { queryByTestId } = render(
        <AuthGuard>
          <Text>Protected content</Text>
        </AuthGuard>,
      );

      expect(queryByTestId('force-link-screen')).toBeNull();
    });
  });

  describe('when forceLinkRequired is true (AC-F01-4)', () => {
    beforeEach(() => {
      mockUseAuthStore.mockReturnValue({
        isAnonymous: true,
        forceLinkRequired: true,
      });
    });

    it('renders ForceLinkScreen instead of children', () => {
      const { getByTestId, queryByText } = render(
        <AuthGuard>
          <Text>Protected content</Text>
        </AuthGuard>,
      );

      expect(getByTestId('force-link-screen')).toBeTruthy();
      expect(queryByText('Protected content')).toBeNull();
    });
  });
});

// ---------------------------------------------------------------------------
// useRequireLinked hook — gates actions behind OAuth linking
// ---------------------------------------------------------------------------

/** Minimal wrapper that exposes hook state for testing. */
const TestWrapper: React.FC<{ onAction: jest.Mock }> = ({ onAction }) => {
  const { requireLinked, sheetProps } = useRequireLinked();
  return (
    <>
      <TouchableOpacity
        testID="trigger"
        onPress={() => requireLinked(onAction)}
      >
        <Text>Trigger</Text>
      </TouchableOpacity>
      <LinkAccountSheet {...sheetProps} />
    </>
  );
};

describe('useRequireLinked', () => {
  let mockAction: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockAction = jest.fn();
    mockUseAuthStore.mockReturnValue({
      isAnonymous: true,
      forceLinkRequired: false,
    });
  });

  it('shows sheet and does not call action when user is anonymous', () => {
    // test_requireLinked_shows_sheet_when_anonymous (FR-5, AC-F01-2, AC-F01-3)
    const { getByTestId } = render(<TestWrapper onAction={mockAction} />);

    fireEvent.press(getByTestId('trigger'));

    expect(getByTestId('link-account-sheet')).toBeTruthy();
    expect(mockAction).not.toHaveBeenCalled();
  });

  it('calls action immediately without sheet when user is linked', () => {
    // test_requireLinked_proceeds_when_linked (FR-5)
    mockUseAuthStore.mockReturnValue({
      isAnonymous: false,
      forceLinkRequired: false,
    });
    const { getByTestId, queryByTestId } = render(
      <TestWrapper onAction={mockAction} />,
    );

    fireEvent.press(getByTestId('trigger'));

    expect(mockAction).toHaveBeenCalledTimes(1);
    expect(queryByTestId('link-account-sheet')).toBeNull();
  });

  it('calls AuthService.linkWithProvider("google") when Google button is tapped', async () => {
    // test_sheet_calls_linkWithProvider_on_tap (FR-7)
    (AuthService.linkWithProvider as jest.Mock).mockResolvedValue(undefined);
    const { getByTestId } = render(<TestWrapper onAction={mockAction} />);

    fireEvent.press(getByTestId('trigger'));
    fireEvent.press(getByTestId('provider-google'));

    expect(AuthService.linkWithProvider).toHaveBeenCalledWith('google');
  });

  it('closes sheet and calls pending action after link succeeds', async () => {
    // test_sheet_dismisses_after_link_success (AC-F01-2, AC-F01-3)
    (AuthService.linkWithProvider as jest.Mock).mockResolvedValue(undefined);
    const { getByTestId, queryByTestId } = render(
      <TestWrapper onAction={mockAction} />,
    );

    fireEvent.press(getByTestId('trigger'));

    await act(async () => {
      fireEvent.press(getByTestId('provider-google'));
    });

    expect(queryByTestId('link-account-sheet')).toBeNull();
    expect(mockAction).toHaveBeenCalledTimes(1);
  });
});
