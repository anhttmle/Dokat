/**
 * Tests for EditOwnerProfileSheet (Design §4.1).
 *
 * Written TDD-style; expected to FAIL until EditOwnerProfileSheet
 * accepts ownerProfile prop and renders a TextInput (Task 7.2).
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import type { OwnerProfile } from '../../services/ProfileService';
import EditOwnerProfileSheet from '../../components/profile/EditOwnerProfileSheet';

const MOCK_PROFILE: OwnerProfile = {
  userId: 'user-1',
  displayName: 'Nguyen Van A',
  avatarUrl: null,
  isAnonymous: false,
  providers: ['google'],
};

describe('EditOwnerProfileSheet', () => {
  it('shows the current display_name in the text input', () => {
    const { getByDisplayValue } = render(
      <EditOwnerProfileSheet ownerProfile={MOCK_PROFILE} />,
    );

    expect(getByDisplayValue('Nguyen Van A')).toBeTruthy();
  });
});
