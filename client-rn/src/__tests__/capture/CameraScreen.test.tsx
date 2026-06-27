/**
 * Tests for CameraScreen — capture state machine + block/retake.
 *
 * Refs: Design §6.4; FR-1, FR-2, FR-6, FR-7; AC-F04-1, AC-F04-2,
 *       AC-F04-5
 */

import React from 'react';
import {
  act,
  fireEvent,
  render,
  waitFor,
} from '@testing-library/react-native';

import CameraScreen from '../../screens/CameraScreen';
import CaptureService from '../../services/capture/CaptureService';

jest.mock('../../services/capture/CaptureService');

const mockProcess = CaptureService.process as jest.Mock;
const BLOCK_MESSAGE = 'Ảnh không hợp lệ — chỉ được chụp thú cưng';

describe('CameraScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('transitions to ready and hands off on valid capture', async () => {
    mockProcess.mockResolvedValue({
      localUri: 'file://small.jpg',
      s3Key: 'posts/u/1_abc.jpg',
      width: 1280,
      height: 720,
      capturedAt: '2026-06-22T00:00:00Z',
    });
    const onReady = jest.fn();

    const { getByTestId } = render(<CameraScreen onReady={onReady} />);
    act(() => getByTestId('camera').props.onCapture('file://raw.jpg'));

    await waitFor(() => expect(onReady).toHaveBeenCalled());
  });

  it('shows block overlay when capture is rejected', async () => {
    mockProcess.mockResolvedValue(null);

    const { getByTestId, findByText } = render(<CameraScreen />);
    act(() => getByTestId('camera').props.onCapture('file://raw.jpg'));

    await findByText(BLOCK_MESSAGE);
  });

  it('resets to idle when retake pressed after block', async () => {
    mockProcess.mockResolvedValue(null);

    const { getByTestId, findByText, queryByText } = render(
      <CameraScreen />,
    );
    act(() => getByTestId('camera').props.onCapture('file://raw.jpg'));
    await findByText(BLOCK_MESSAGE);

    fireEvent.press(getByTestId('retake-button'));

    expect(queryByText(BLOCK_MESSAGE)).toBeNull();
  });

  it('configures the back camera', () => {
    const { getByTestId } = render(<CameraScreen />);

    expect(getByTestId('camera').props.position).toBe('back');
  });
});
