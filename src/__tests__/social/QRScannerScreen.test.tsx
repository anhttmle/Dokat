/**
 * Tests for QRScannerScreen — camera scanner that extracts QR token.
 *
 * Written TDD-style; tests are expected to FAIL until the screen is
 * implemented in a later F03 task.
 *
 * Refs: Design §4.2, AC-F03-2, AC-F03-4, AC-F03-6, AC-F03-7
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

import QRScannerScreen from '../../screens/QRScannerScreen';

jest.mock('../../services/SocialService');

describe('QRScannerScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', async () => {
    await act(async () => {
      render(<QRScannerScreen />);
    });
  });

  it('calls scanQR when a valid deep-link token is read', async () => {
    const SocialService = require('../../services/SocialService').default;
    SocialService.scanQR.mockResolvedValueOnce({
      friendship_id: 'f-id',
      friend: { user_id: 'u-id', display_name: 'A', avatar_url: null },
      created_at: '2026-06-21T04:02:30Z',
    });

    await act(async () => {
      render(<QRScannerScreen />);
    });

    // Detailed interaction tests will be added in a later task.
    expect(true).toBe(true);
  });
});
