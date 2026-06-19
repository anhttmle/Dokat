/**
 * Tests for AuthGuard component.
 * Renders children normally; renders ForceLinkScreen when
 * forceLinkRequired is true (AC-F01-4).
 *
 * Design ref: §4.1
 */

import React from 'react';
import { Text } from 'react-native';
import { render } from '@testing-library/react-native';

import AuthGuard from '../../components/auth/AuthGuard';
import useAuthStore from '../../stores/useAuthStore';

jest.mock('../../stores/useAuthStore');

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
