/**
 * CameraScreen — in-app back-camera capture with AI validation.
 *
 * Manages the capture state machine
 * (idle → capturing → validating → blocked | ready). On capture it
 * delegates to CaptureService.process: a CapturedPhoto hands off to
 * F05 via onReady; a null result shows the block overlay with a
 * retake action that returns to idle (FR-7, AC-F04-5).
 *
 * The camera is rendered as a mock-friendly View (testID="camera",
 * position="back") per DL-F03-11/DL-F04-03; the native camera
 * library is integrated in a later task.
 *
 * Refs: Design §1.1, §1.2, §1.3, §4.1, §5; FR-1, FR-2, FR-6, FR-7;
 *       AC-F04-1, AC-F04-2, AC-F04-5
 */

import React from 'react';
import { Pressable, Text, View } from 'react-native';

import CaptureService, {
  type CapturedPhoto,
} from '../services/capture/CaptureService';

const BLOCK_MESSAGE = 'Ảnh không hợp lệ — chỉ được chụp thú cưng';

type CaptureState =
  | 'idle'
  | 'capturing'
  | 'validating'
  | 'blocked'
  | 'ready';

export interface CameraScreenProps {
  /** Current user id, used to build the photo's S3 key. */
  userId?: string;
  /** Handoff callback for a valid CapturedPhoto (F05). */
  onReady?: (photo: CapturedPhoto) => void;
}

const CameraScreen: React.FC<CameraScreenProps> = ({
  userId = '',
  onReady,
}) => {
  const [state, setState] = React.useState<CaptureState>('idle');

  /**
   * Called by the camera element when a raw image is captured.
   *
   * Runs validation + compression; routes to ready (handoff) or
   * blocked based on the CaptureService result.
   */
  const handleCapture = React.useCallback(
    async (localUri: string) => {
      setState('validating');
      const photo = await CaptureService.process(localUri, userId);
      if (photo) {
        setState('ready');
        onReady?.(photo);
      } else {
        setState('blocked');
      }
    },
    [userId, onReady],
  );

  const handleRetake = React.useCallback(() => {
    setState('idle');
  }, []);

  const cameraProps = {
    testID: 'camera',
    position: 'back',
    onCapture: handleCapture,
  } as any; // eslint-disable-line @typescript-eslint/no-explicit-any

  return (
    <View>
      <View {...cameraProps} />
      {state === 'blocked' && (
        <View testID="block-overlay">
          <Text>{BLOCK_MESSAGE}</Text>
          <Pressable testID="retake-button" onPress={handleRetake}>
            <Text>Chụp lại</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
};

export default CameraScreen;
