/**
 * AuthGuard — wraps screens that need force-link enforcement.
 * useRequireLinked — hook that gates actions behind OAuth linking.
 *
 * Behaviour (AC-F01-2, AC-F01-3, AC-F01-4, Design §4.1):
 *   - AuthGuard: when forceLinkRequired is true, renders ForceLinkScreen.
 *   - useRequireLinked: when isAnonymous, shows LinkAccountSheet before
 *     the action; when linked, calls the action immediately.
 */

import React, { useRef, useState } from 'react';

import ForceLinkScreen from '../../screens/auth/ForceLinkScreen';
import useAuthStore from '../../stores/useAuthStore';

interface Props {
  children: React.ReactNode;
}

const AuthGuard: React.FC<Props> = ({ children }) => {
  const { forceLinkRequired } = useAuthStore();

  if (forceLinkRequired) {
    return <ForceLinkScreen />;
  }

  return <>{children}</>;
};

export default AuthGuard;

// ---------------------------------------------------------------------------

interface SheetProps {
  visible: boolean;
  onLinked: () => void;
  onDismiss: () => void;
}

interface RequireLinkedResult {
  requireLinked: (action: () => void) => void;
  sheetProps: SheetProps;
}

/**
 * Hook that gates an action behind OAuth account linking.
 *
 * If the user is already linked, ``requireLinked(action)`` calls
 * ``action()`` immediately.  If they are anonymous, it stores the
 * action and shows ``LinkAccountSheet`` via the returned ``sheetProps``.
 * The sheet's ``onLinked`` callback fires the stored action and hides
 * the sheet.
 *
 * Design §4.1 (FR-5; AC-F01-2, AC-F01-3).
 */
export const useRequireLinked = (): RequireLinkedResult => {
  const { isAnonymous } = useAuthStore();
  const [sheetVisible, setSheetVisible] = useState(false);
  const pendingAction = useRef<(() => void) | null>(null);

  const requireLinked = (action: () => void): void => {
    if (!isAnonymous) {
      action();
      return;
    }
    pendingAction.current = action;
    setSheetVisible(true);
  };

  const sheetProps: SheetProps = {
    visible: sheetVisible,
    onLinked: () => {
      setSheetVisible(false);
      pendingAction.current?.();
    },
    onDismiss: () => setSheetVisible(false),
  };

  return { requireLinked, sheetProps };
};
